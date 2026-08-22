# =============================================================
# plc_service.py — Servicio Windows: PLCCurvasTueste
# Lee %M30 cada 1 seg → si = 1 inserta fila en tblConsumosCurvas
#
# INSTALAR (cmd como Administrador):
#   python plc_service.py install
#   python plc_service.py start
#
# PROBAR en consola:
#   python plc_service.py debug
#
# DETENER / DESINSTALAR:
#   python plc_service.py stop
#   python plc_service.py remove
# =============================================================

import sys
import time
import traceback
from datetime import datetime

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
def procesar_ciclo(lector: PLCReader, escritor: SQLWriter, log, estado: dict):
    """
    Un ciclo cada 1 segundo:
    - Lee %M30
    - Si = 1 → lee %MW80-83 → inserta fila en tblConsumosCurvas → loguea
    - Si cambia de 1→0 loguea fin del datalog
    - estado['activo'] rastrea si el tueste estaba activo en el ciclo anterior
    """
    try:
        trigger = lector.leer_trigger()
    except IOError as e:
        log.warning(f"Sin respuesta al leer %M30: {e}")
        return

    if trigger is None:
        log.warning("Respuesta nula de %M30 — PLC no responde")
        return

    # Detectar inicio de tueste
    if trigger and not estado["activo"]:
        estado["activo"] = True
        estado["inicio"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Leer IdOrden y Bache una sola vez al inicio del ciclo
        try:
            lector.leer_orden()
            log.info(
                f"▶ %M30 activado — iniciando datalog | "
                f"IdOrden={lector._id_orden} | Bache={lector._bache} | "
                f"Desde {estado['inicio']}"
            )
        except Exception as e:
            log.warning(f"No se pudo leer IdOrden/Bache: {e}")

    # Detectar fin de tueste
    if not trigger and estado["activo"]:
        estado["activo"] = False
        log.info(
            f"■ %M30 desactivado — datalog finalizado | "
            f"Inicio: {estado['inicio']} | "
            f"Registros: {estado['count']}"
        )
        estado["count"] = 0
        return

    if not trigger:
        return  # Normal: esperando que empiece el tueste

    # ── %M30 = 1 → leer y guardar ────────────────────────────
    try:
        datos = lector.leer_datos()
    except Exception as e:
        log.error(f"Error leyendo %MW80-83: {e}")
        return

    try:
        id_ins = escritor.insertar(datos)
        estado["count"] += 1
        log_registro_insertado(log, id_ins, datos)
    except Exception as e:
        log_error_insercion(log, str(e), datos)


# =============================================================
# SERVICIO WINDOWS
# =============================================================
class PLCCurvasService(win32serviceutil.ServiceFramework):

    _svc_name_         = "PLCCurvasTueste"
    _svc_display_name_ = "PLC Curvas Tueste — Tiempo Real"
    _svc_description_  = (
        "Lee %M30 cada segundo y guarda la curva de tueste en tiempo real "
        "(%MW80-83) en dbo.tblConsumosCurvas (SQL Server)."
    )

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event = win32event.CreateEvent(None, 0, 0, None)
        self._running    = True
        self.log         = crear_logger("PLCCurvas")

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self._stop_event)
        self._running = False
        self.log.info("Servicio detenido por Windows.")

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )
        self.log.info(
            f"═══ Servicio PLCCurvasTueste iniciado ═══  "
            f"Poll %M30 cada {POLL_SEG}s"
        )
        self._loop()

    def _loop(self):
        lector   = PLCReader()
        escritor = SQLWriter()
        estado   = {"activo": False, "inicio": None, "count": 0}

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
                procesar_ciclo(lector, escritor, self.log, estado)
            except Exception:
                self.log.error(f"Error inesperado:\n{traceback.format_exc()}")

            # Espera POLL_SEG segundos verificando parada cada 0.25s
            for _ in range(int(POLL_SEG / 0.25)):
                if not self._running:
                    break
                time.sleep(0.25)

        lector.desconectar()
        escritor.desconectar()
        self.log.info("Servicio finalizado correctamente.")


# =============================================================
# MODO DEBUG
# =============================================================
def _modo_debug():
    import config
    log = crear_logger("PLCCurvasDebug")
    log.info(
        f"[DEBUG] Poll %M30 cada {POLL_SEG}s — Ctrl+C para salir\n"
        f"  PLC   : {config.PLC_HOST}:{config.PLC_PORT}\n"
        f"  Tabla : dbo.tblConsumosCurvas\n"
        f"  SP    : dbo.spInsertarConsumosCurvas\n"
        f"  Log   : {config.LOG_FILE}"
    )

    lector   = PLCReader()
    escritor = SQLWriter()
    estado   = {"activo": False, "inicio": None, "count": 0}

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
            procesar_ciclo(lector, escritor, log, estado)
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
        win32serviceutil.HandleCommandLine(PLCCurvasService)