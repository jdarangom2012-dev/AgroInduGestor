# =============================================================
# plc_reader.py — Lectura Modbus TCP del M221
# Direcciones exactas PROD_TE_* según tabla definitiva
# =============================================================
#
# MAPA DE REGISTROS (%MW600 al %MW637 = 38 words):
#
#  %MW600  PROD_TE_ORDEN_OP        UINT 16bit  → IdOrden (número de OP)
#  %MW601  PROD_TE_ORDEN_BACHE     UINT 16bit  → Bache
#  %MW602  PROD_TE_CLIENTEID       UINT 16bit  → IdCliente
#  %MW603  PROD_TE_CLIENTENOMBRE   STRING 20ch → Nombre (10 words: MW603-612)
#  %MW613  PROD_TE_PERFILTUESTE    UINT 16bit  → solo log
#  %MF614  PROD_TE_PESOCV          REAL 32bit  → PesoCv  (MW614+MW615)
#  %MD616  PROD_TE_FECHAINIORDEN   BCD  32bit  → FechaHoraIni parte fecha (MW616+MW617)
#  %MD618  PROD_TE_HORAINIORDEN    BCD  32bit  → FechaHoraIni parte hora  (MW618+MW619)
#  %MW620  PROD_TE_CONSUMOGAS      UINT 16bit  → ConsumoGas
#  %MW621  PROD_TE_CONSUMOKWH      UINT 16bit  → ConsumoKwh
#  %MF622  PROD_TE_PESOCT          REAL 32bit  → PesoCt  (MW622+MW623)
#  %MW624  PROD_TE_TEMPDESH        UINT 16bit  → TempDesh
#  %MW625  PROD_TE_TIEMDESH        BCD  16bit  → TiempoDesh_seg
#  %MW626  PROD_TE_TEMPRECU        UINT 16bit  → TempRecu
#  %MW627  PROD_TE_TIEMRECU        BCD  16bit  → TiempoRecu_seg
#  %MW628  PROD_TE_TEMP1CRK        UINT 16bit  → Temp1Crack
#  %MW629  PROD_TE_TIEM1CRK        BCD  16bit  → Tiempo1Crack_seg
#  %MW630  PROD_TE_TEMPFINCURVA    UINT 16bit  → TempfinCurva
#  %MW631  PROD_TE_TIEMFINCURVA    BCD  16bit  → TiempofinCurva_seg
#  %MD632  PROD_TE_FECHAFINORDEN   BCD  32bit  → FechaHoraFin parte fecha (MW632+MW633)
#  %MD634  PROD_TE_HORAFINORDEN    BCD  32bit  → FechaHoraFin parte hora  (MW634+MW635)
#  %MW636  PROD_TE_TIEMPOTUESTE    BCD  16bit  → TiempoTueste_seg
#  %MW637  PROD_TE_TIEMPOENFR      BCD  16bit  → TiempoEnfriamiento_seg
#
#  DISPARADOR:
#  %M93    PROD_ORDEN_COMPLETADA   BIT  → se desactiva SOLO por el PLC
#                                         Python NO necesita resetearlo

from typing import Optional
import struct
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
from config import PLC_HOST, PLC_PORT, PLC_UNIT_ID, COIL_TRIGGER

# Bloque único: %MW600 al %MW637 = 38 words
BLOQUE_START = 600
BLOQUE_COUNT = 38   # 637 - 600 + 1


# =============================================================
# DECODIFICADORES DE TIPOS DE DATO DEL M221
# =============================================================

def _bcd16_a_seg(word: int) -> int:
    """BCD 16 bit formato MM:SS → segundos totales."""
    mm = ((word >> 12) & 0xF) * 10 + ((word >> 8) & 0xF)
    ss = ((word >> 4)  & 0xF) * 10 + (word        & 0xF)
    return mm * 60 + ss


def _bcd32_fecha_hora_a_int(fecha_dword: int, hora_dword: int) -> int:
    """
    Convierte dos DWORD BCD (fecha + hora del M221) en un entero
    compacto con formato YYYYMMDDHHmmss.
    Formato M221 fecha BCD: byte0=DD, byte1=MM, byte2=AñoHi, byte3=AñoLo
    Formato M221 hora  BCD: byte0=reservado, byte1=HH, byte2=MM, byte3=SS
    """
    def bcd_byte(b): return (b >> 4) * 10 + (b & 0xF)

    fb = fecha_dword.to_bytes(4, 'big')
    hb = hora_dword.to_bytes(4, 'big')

    dd   = bcd_byte(fb[0]);  mm   = bcd_byte(fb[1])
    anhi = bcd_byte(fb[2]);  anlo = bcd_byte(fb[3])
    yyyy = anhi * 100 + anlo

    HH = bcd_byte(hb[1]);  MI = bcd_byte(hb[2]);  SS = bcd_byte(hb[3])

    return int(f"{yyyy:04d}{mm:02d}{dd:02d}{HH:02d}{MI:02d}{SS:02d}")


def _udint(regs: list, idx: int) -> int:
    """2 words → UDINT 32 bit (word alto primero)."""
    return ((regs[idx] & 0xFFFF) << 16) | (regs[idx + 1] & 0xFFFF)


def _real(regs: list, idx: int) -> float:
    """2 words → IEEE 754 float 32 bit."""
    raw = struct.pack('>HH', regs[idx], regs[idx + 1])
    val = struct.unpack('>f', raw)[0]
    return round(val, 4)


def _string(regs: list, idx: int, num_words: int = 10) -> str:
    """num_words words → STRING M221 (byte alto = char[n], byte bajo = char[n+1])."""
    chars = []
    for i in range(num_words):
        w = regs[idx + i]
        hi, lo = (w >> 8) & 0xFF, w & 0xFF
        if hi: chars.append(chr(hi))
        if lo: chars.append(chr(lo))
    return "".join(chars).strip("\x00").strip()[:20]


def _off(addr: int) -> int:
    """Índice dentro del bloque leído (base BLOQUE_START=600)."""
    return addr - BLOQUE_START


# =============================================================
# PARSEO DEL BLOQUE %MW600-637
# =============================================================
def _parsear(regs: list) -> dict:
    """
    Transforma los 38 words leídos en el dict exacto que
    sql_writer.insertar() necesita.
    """
    # ── Identificación ───────────────────────────────────────
    id_orden       = regs[_off(600)]                   # %MW600 UINT — número de OP
    bache          = regs[_off(601)]                   # %MW601 UINT — número de bache
    id_cliente     = regs[_off(602)]                   # %MW602 UINT
    nombre         = _string(regs, _off(603), 10)      # %MW603-612 STRING 20char
    perfil_tueste  = regs[_off(613)]                   # %MW613 solo log

    # ── Pesos ────────────────────────────────────────────────
    peso_cv        = _real(regs, _off(614))            # %MF614 REAL (MW614+MW615)
    peso_ct        = _real(regs, _off(622))            # %MF622 REAL (MW622+MW623)

    # ── Fechas/horas → int compacto YYYYMMDDHHmmss ──────────
    fecha_ini_dw   = _udint(regs, _off(616))           # %MD616 (MW616+MW617)
    hora_ini_dw    = _udint(regs, _off(618))           # %MD618 (MW618+MW619)
    fecha_fin_dw   = _udint(regs, _off(632))           # %MD632 (MW632+MW633)
    hora_fin_dw    = _udint(regs, _off(634))           # %MD634 (MW634+MW635)

    fecha_hora_ini = _bcd32_fecha_hora_a_int(fecha_ini_dw, hora_ini_dw)
    fecha_hora_fin = _bcd32_fecha_hora_a_int(fecha_fin_dw, hora_fin_dw)

    # ── Consumos ─────────────────────────────────────────────
    consumo_gas    = float(regs[_off(620)])            # %MW620
    consumo_kwh    = float(regs[_off(621)])            # %MW621

    # ── Temperaturas → float ─────────────────────────────────
    temp_desh      = float(regs[_off(624)])            # %MW624
    temp_recu      = float(regs[_off(626)])            # %MW626
    temp_1crk      = float(regs[_off(628)])            # %MW628
    temp_fin       = float(regs[_off(630)])            # %MW630

    # ── Tiempos BCD 16bit → segundos ─────────────────────────
    tiem_desh_seg      = _bcd16_a_seg(regs[_off(625)])  # %MW625
    tiem_recu_seg      = _bcd16_a_seg(regs[_off(627)])  # %MW627
    tiem_1crk_seg      = _bcd16_a_seg(regs[_off(629)])  # %MW629
    tiem_fin_seg       = _bcd16_a_seg(regs[_off(631)])  # %MW631
    tiem_tueste_seg    = _bcd16_a_seg(regs[_off(636)])  # %MW636
    tiem_enfr_seg      = _bcd16_a_seg(regs[_off(637)])  # %MW637

    # ── Rendimiento calculado ────────────────────────────────
    rendimiento = round((peso_ct / peso_cv) * 100.0, 2) if peso_cv else 0.0

    return {
        # Campos que van al SP
        "IdOrden":                id_orden,
        "Bache":                  bache,
        "IdCliente":              id_cliente,
        "PesoCv":                 peso_cv,
        "PesoCt":                 peso_ct,
        "TempDesh":               temp_desh,
        "TiempoDesh_seg":         tiem_desh_seg,
        "TempRecu":               temp_recu,
        "TiempoRecu_seg":         tiem_recu_seg,
        "Temp1Crack":             temp_1crk,
        "Tiempo1Crack_seg":       tiem_1crk_seg,
        "TempfinCurva":           temp_fin,
        "TiempofinCurva_seg":     tiem_fin_seg,
        "TiempoTueste_seg":       tiem_tueste_seg,
        "TiempoEnfriamiento_seg": tiem_enfr_seg,
        "Rendimiento":            rendimiento,
        "ConsumoGas":             consumo_gas,
        "ConsumoKwh":             consumo_kwh,
        "FechaHoraIni":           fecha_hora_ini,
        "FechaHoraFin":           fecha_hora_fin,
        "Nombre":                 nombre,
        # Solo para el log
        "_PerfilTueste":          perfil_tueste,
    }


# =============================================================
# CLASE PRINCIPAL
# =============================================================
class PLCReader:

    def __init__(self):
        self.client: Optional[ModbusTcpClient] = None

    def conectar(self) -> bool:
        try:
            self.client = ModbusTcpClient(host=PLC_HOST, port=PLC_PORT, timeout=5)
            ok = self.client.connect()
            if not ok:
                raise ConnectionError(f"PLC {PLC_HOST}:{PLC_PORT} rechazó la conexión")
            return ok
        except Exception as e:
            raise ConnectionError(str(e))

    def desconectar(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass

    def _asegurar_conexion(self):
        if not self.client or not self.client.is_socket_open():
            self.conectar()

    # ── %M93 ─────────────────────────────────────────────────
    def leer_trigger(self) -> Optional[bool]:
        """
        Lee el coil %M93 (PROD_ORDEN_COMPLETADA).
        Retorna True/False o None si no responde.
        NOTA: el PLC desactiva este bit solo — Python NO lo resetea.
        """
        self._asegurar_conexion()
        try:
            r = self.client.read_coils(COIL_TRIGGER, count=1, device_id=PLC_UNIT_ID)
            if r.isError():
                return None
            return bool(r.bits[0])
        except ModbusException as e:
            raise IOError(f"Error leyendo %M{COIL_TRIGGER}: {e}")

    # ── Lectura del bloque %MW600-637 ────────────────────────
    def leer_datos(self) -> dict:
        """
        Lee los 38 Holding Registers (%MW600-637) en una sola
        petición Modbus y retorna el dict listo para el SP.
        """
        self._asegurar_conexion()
        r = self.client.read_holding_registers(BLOQUE_START, count=BLOQUE_COUNT, device_id=PLC_UNIT_ID)
        if r.isError():
            raise IOError(
                f"Error leyendo bloque %MW{BLOQUE_START}-"
                f"%MW{BLOQUE_START + BLOQUE_COUNT - 1}: {r}"
            )
        return _parsear(r.registers)

    # ── Resetear %M93 tras INSERT exitoso ────────────────────
    def resetear_trigger(self):
        """
        Escribe False en %M93 para indicar al PLC que el registro
        fue insertado correctamente en la base de datos.
        Solo se llama cuando el INSERT fue exitoso.
        """
        self._asegurar_conexion()
        try:
            self.client.write_coil(
                COIL_TRIGGER, False,
                count=1, device_id=PLC_UNIT_ID
            )
        except Exception as e:
            raise IOError(f"Error reseteando %M{COIL_TRIGGER}: {e}")