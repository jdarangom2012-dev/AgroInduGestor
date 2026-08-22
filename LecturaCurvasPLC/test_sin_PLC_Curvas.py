# =============================================================
# test_sin_plc.py — Prueba spInsertarConsumosCurvas sin PLC
# Ejecutar desde la carpeta PLCServiceCurvas:
#   python test_sin_plc.py
# =============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sql_writer import SQLWriter
from logger_setup import crear_logger, log_registro_insertado, log_error_insercion

log = crear_logger("TestCurvasSinPLC")

# Simula 5 segundos de curva con datos ficticios
registros_prueba = [
    {"SpTemperatura": 150.0, "TempReal": 148.5, "PctAire": 45.0, "PctGas": 60.0},
    {"SpTemperatura": 155.0, "TempReal": 152.3, "PctAire": 45.0, "PctGas": 62.0},
    {"SpTemperatura": 160.0, "TempReal": 158.7, "PctAire": 46.0, "PctGas": 63.0},
    {"SpTemperatura": 165.0, "TempReal": 163.1, "PctAire": 46.0, "PctGas": 64.0},
    {"SpTemperatura": 170.0, "TempReal": 168.9, "PctAire": 47.0, "PctGas": 65.0},
]

log.info("=" * 55)
log.info("PRUEBA SIN PLC — insertando 5 filas de curva")
log.info("=" * 55)

escritor = SQLWriter()

try:
    escritor.conectar()
    log.info("✔ Conectado a SQL Server")
except Exception as e:
    log.error(f"✘ No se pudo conectar a SQL Server: {e}")
    sys.exit(1)

exitosos = 0
for i, datos in enumerate(registros_prueba, 1):
    try:
        id_ins = escritor.insertar(datos)
        log_registro_insertado(log, id_ins, datos)
        exitosos += 1
    except Exception as e:
        log_error_insercion(log, str(e), datos)

escritor.desconectar()

print(f"\n✔ {exitosos}/{len(registros_prueba)} registros insertados en tblConsumosCurvas")
print(f"  Revisa: SELECT TOP 5 * FROM dbo.tblConsumosCurvas ORDER BY Id DESC")