# =============================================================
# test_sin_plc.py — Prueba el SP y el log sin necesitar el PLC
# Ejecutar desde la carpeta del servicio:
#   python test_sin_plc.py
# =============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sql_writer import SQLWriter
from logger_setup import crear_logger, log_registro_insertado, log_error_insercion

log = crear_logger("TestSinPLC")

# ── Datos de prueba — simulan lo que vendría del PLC ─────────
datos_prueba = {
    "IdOrden":                1001,
    "Bache":                  1,
    "IdCliente":              5,
    "PesoCv":                 50.5,       # kg café verde
    "PesoCt":                 42.3,       # kg café tostado
    "TempDesh":               150.0,      # °C
    "TiempoDesh_seg":         300,        # 5 minutos
    "TempRecu":               175.0,
    "TiempoRecu_seg":         240,        # 4 minutos
    "Temp1Crack":             196.0,
    "Tiempo1Crack_seg":       480,        # 8 minutos
    "TempfinCurva":           210.0,
    "TiempofinCurva_seg":     600,        # 10 minutos
    "TiempoTueste_seg":       720,        # 12 minutos
    "TiempoEnfriamiento_seg": 180,        # 3 minutos
    "Rendimiento":            83.76,      # % calculado
    "ConsumoGas":             12.0,       # nm3
    "ConsumoKwh":             8.5,        # kWh
    "FechaHoraIni":           20260704120000,  # YYYYMMDDHHmmss
    "FechaHoraFin":           20260704121200,
    "Nombre":                 "Cliente Prueba",
}

log.info("=" * 55)
log.info("PRUEBA SIN PLC — insertando datos ficticios")
log.info("=" * 55)

escritor = SQLWriter()

try:
    escritor.conectar()
    log.info("✔ Conectado a SQL Server")
except Exception as e:
    log.error(f"✘ No se pudo conectar a SQL Server: {e}")
    sys.exit(1)

try:
    id_ins = escritor.insertar(datos_prueba)
    log_registro_insertado(
        log,
        tabla=f"dbo.tblConsumosTueste (Id={id_ins})",
        datos=datos_prueba
    )
    print(f"\n✔ ÉXITO — Registro insertado con Id={id_ins}")
    print(f"  Revisa la tabla: SELECT TOP 1 * FROM dbo.tblConsumosTueste ORDER BY Id DESC")

except Exception as e:
    log_error_insercion(log, tabla="dbo.tblConsumosTueste", error=str(e), datos=datos_prueba)
    print(f"\n✘ ERROR — {e}")

finally:
    escritor.desconectar()