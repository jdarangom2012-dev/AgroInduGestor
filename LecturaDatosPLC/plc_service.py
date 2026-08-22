# =============================================================
# plc_service.py — Servicio Windows: PLCConsumosTostion
# Lee %M93 cada 2 seg → si = 1 lee PLC → sp_InsertarCurvaTueste
#                                        → tblConsumosTostion
#                                        → log completo
#
# NOTA: Python apaga %M93 solo cuando el INSERT fue exitoso.
#       Python solo lo lee, no lo resetea.
#
# INSTALAR (cmd como Administrador):
#   python plc_service.py install
#   python plc_service.py start
#
# PROBAR en consola:
#   python plc_service.py debug
#
# GESTIÓN:
#   python plc_service.py stop
#   python plc_service.py remove
# =============================================================

import sys
import time
import traceback

import win32serviceutil
import win32service
import win32event
import servicemanager

from config import POLL_SEG
from logger_setup import crear_logger, log_registro_insertado, log_error_insercion
from plc_reader import PLCReader
from sql_writer import SQLWriter


# =============================================================
# LÓGICA DE NEGOCIO
# =============================================================

# Rastrear el estado anterior del bit para detectar flanco ascendente
# (evitar insertar múltiples veces si el bit permanece en 1 varios ciclos)
_trigger_anterior = False


def procesar_ciclo(lector: PLCReader, escritor: SQLWriter, log):
    """
    Detecta el FLANCO ASCENDENTE de %M93 (0→1).
    Solo inserta UNA VEZ por activación, aunque el bit tarde
    varios ciclos en bajar (el PLC lo desactiva solo).
    """
    global _trigger_anterior

    # ── Leer bit %M93 ────────────────────────────────────────
    try:
        trigger = lector.leer_trigger()
    except IOError as e:
        log.warning(f"Sin respuesta al leer %M93: {e}")
        _trigger_anterior = False
        return

    if trigger is None:
        log.warning("Respuesta nula de %M93 — PLC no responde")
        _trigger_anterior = False
        return

    # Detectar flanco 0→1 (evita doble inserción)
    flanco = trigger and not _trigger_anterior
    _trigger_anterior = trigger

    if not flanco:
        return   # Bit en 0, o ya estaba en 1 desde el ciclo anterior

    # ── Flanco detectado → leer datos del PLC ────────────────
    log.info("▶ %M93 activado (PROD_ORDEN_COMPLETADA) — leyendo %MW600-637")

    try:
        datos = lector.leer_datos()
    except Exception as e:
        log.error(f"Error leyendo bloque Modbus: {e}\n{traceback.format_exc()}")
        return

    # ── Insertar en SQL Server ────────────────────────────────
    try:
        id_ins = escritor.insertar(datos)
        datos_log = {k: v for k, v in datos.items() if not k.startswith("_")}
        log_registro_insertado(
            log,
            tabla=f"dbo.tblConsumosTueste (Id={id_ins})",
            datos=datos_log
        )
        # ── INSERT exitoso → apagar %M93 ─────────────────────
        try:
            lector.resetear_trigger()
            log.info(f"✔ %M93 apagado — INSERT confirmado (Id={id_ins})")
        except IOError as e:
            log.warning(f"No se pudo apagar %M93: {e}")

    except Exception as e:
        datos_log = {k: v for k, v in datos.items() if not k.startswith("_")}
        log_error_insercion(
            log,
            tabla="dbo.tblConsumosTueste",
            error=str(e),
            datos=datos_log
        )
        # Si el INSERT falló NO apagamos %M93 — el PLC sabrá que hubo error


# =============================================================
# SERVICIO WINDOWS
# =============================================================
class PLCService(win32serviceutil.ServiceFramework):

    _svc_name_         = "PLCConsumosTostion"
    _svc_display_name_ = "PLC Consumos Tostion — Modicon M221"
    _svc_description_  = (
        "Lee %M93 cada 2 seg. Al detectar flanco ascendente lee %MW600-637 "
        "y guarda la curva de tueste en dbo.tblConsumosTostion (SQL Server)."
    )

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event = win32event.CreateEvent(None, 0, 0, None)
        self._running    = True
        self.log         = crear_logger("PLCService")

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self._stop_event)
        self._running = False
        self.log.info("Solicitud de parada recibida.")

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )
        self.log.info(
            f"═══ Servicio PLCConsumosTostion iniciado ═══  "
            f"PLC={__import__('config').PLC_HOST} | "
            f"Poll %M93 cada {POLL_SEG}s | Registros en %MW600-637"
        )
        self._loop()

    def _loop(self):
        lector   = PLCReader()
        escritor = SQLWriter()

        try:
            lector.conectar()
            self.log.info("✔ Conectado al PLC")
        except Exception as e:
            self.log.error(f"Conexión inicial al PLC fallida: {e}")

        try:
            escritor.conectar()
            self.log.info("✔ Conectado a SQL Server")
        except Exception as e:
            self.log.error(f"Conexión inicial a SQL Server fallida: {e}")

        while self._running:
            try:
                procesar_ciclo(lector, escritor, self.log)
            except Exception:
                self.log.error(
                    f"Error inesperado en ciclo:\n{traceback.format_exc()}"
                )

            for _ in range(int(POLL_SEG / 0.5)):
                if not self._running:
                    break
                time.sleep(0.5)

        lector.desconectar()
        escritor.desconectar()
        self.log.info("Servicio detenido correctamente.")


# =============================================================
# MODO DEBUG
# =============================================================
def _modo_debug():
    import config
    log = crear_logger("PLCDebug")
    log.info(
        f"[DEBUG] Poll %M93 cada {POLL_SEG}s — Ctrl+C para salir\n"
        f"  PLC     : {config.PLC_HOST}:{config.PLC_PORT}\n"
        f"  Bloque  : %MW600-637\n"
        f"  Tabla   : dbo.tblConsumosTostion\n"
        f"  SP      : dbo.sp_InsertarCurvaTueste\n"
        f"  Log     : {config.LOG_FILE}"
    )

    lector   = PLCReader()
    escritor = SQLWriter()

    try:
        lector.conectar()
        log.info("✔ PLC conectado")
    except Exception as e:
        log.error(f"PLC: {e}")

    try:
        escritor.conectar()
        log.info("✔ SQL Server conectado")
    except Exception as e:
        log.error(f"SQL: {e}")

    try:
        while True:
            procesar_ciclo(lector, escritor, log)
            time.sleep(POLL_SEG)
    except KeyboardInterrupt:
        log.info("Detenido manualmente.")
    finally:
        lector.desconectar()
        escritor.desconectar()


# =============================================================
if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "debug":
        _modo_debug()
    else:
        win32serviceutil.HandleCommandLine(PLCService)