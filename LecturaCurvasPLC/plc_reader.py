# =============================================================
# plc_reader.py — Servicio PLCCurvasTueste
# Compatible con pymodbus 3.13.1
# Lee:
#   %M30        → trigger (datalog activo)
#   %MW80-83    → curva en tiempo real
#   %MW500-501  → IdOrden y Bache del tueste en curso
# =============================================================
from typing import Optional
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
from config import PLC_HOST, PLC_PORT, PLC_UNIT_ID, COIL_TRIGGER, REGS_START, REGS_COUNT

# Registros de identificación de la orden
ORDEN_START = 500   # %MW500 = IdOrden (UINT 16bit)
ORDEN_COUNT = 2     # %MW500 + %MW501


class PLCReader:

    def __init__(self):
        self.client: Optional[ModbusTcpClient] = None
        # Cache de IdOrden y Bache — se leen una vez al inicio del tueste
        self._id_orden: int = 0
        self._bache:    int = 0

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

    # ── %M30 ─────────────────────────────────────────────────
    def leer_trigger(self) -> Optional[bool]:
        """Lee %M30. True = datalog activo, False = inactivo."""
        self._asegurar_conexion()
        try:
            r = self.client.read_coils(COIL_TRIGGER, count=1, device_id=PLC_UNIT_ID)
            if r.isError():
                return None
            return bool(r.bits[0])
        except ModbusException as e:
            raise IOError(f"Error leyendo %M{COIL_TRIGGER}: {e}")

    # ── %MW500-501: IdOrden y Bache ──────────────────────────
    def leer_orden(self):
        """
        Lee %MW500 (IdOrden) y %MW501 (Bache) y los guarda en cache.
        Se llama una sola vez al detectar el inicio del tueste.
        """
        self._asegurar_conexion()
        try:
            r = self.client.read_holding_registers(
                ORDEN_START, count=ORDEN_COUNT, device_id=PLC_UNIT_ID
            )
            if r.isError():
                raise IOError(f"Error leyendo %MW{ORDEN_START}-{ORDEN_START+ORDEN_COUNT-1}: {r}")
            self._id_orden = r.registers[0]   # %MW500
            self._bache    = r.registers[1]   # %MW501
        except ModbusException as e:
            raise IOError(f"Error leyendo orden: {e}")

    # ── %MW80-83: Curva en tiempo real ───────────────────────
    def leer_datos(self) -> dict:
        """
        Lee los 4 registros de curva (%MW80-83) y los combina
        con el IdOrden y Bache que se leyeron al inicio del ciclo.
        """
        self._asegurar_conexion()
        try:
            r = self.client.read_holding_registers(
                REGS_START, count=REGS_COUNT, device_id=PLC_UNIT_ID
            )
            if r.isError():
                raise IOError(f"Error leyendo %MW{REGS_START}-{REGS_START+REGS_COUNT-1}: {r}")

            regs = r.registers
            return {
                "IdOrden":       self._id_orden,    # %MW500 (leído al inicio)
                "Bache":         self._bache,        # %MW501 (leído al inicio)
                "SpTemperatura": regs[0] / 10.0,    # %MW80
                "TempReal":      regs[1] / 10.0,    # %MW81
                "PctAire":       regs[2] / 10.0,    # %MW82
                "PctGas":        regs[3] / 10.0,    # %MW83
            }
        except ModbusException as e:
            raise IOError(f"Error leyendo registros curva: {e}")