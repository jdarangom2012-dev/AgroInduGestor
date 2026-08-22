# =============================================================
# logger_setup.py — Logging con rotación
# =============================================================
import logging
import os
from logging.handlers import RotatingFileHandler
from config import LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT


def crear_logger(nombre: str = "PLCCurvas") -> logging.Logger:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    logger = logging.getLogger(nombre)
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    fh = RotatingFileHandler(
        LOG_FILE, maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def log_registro_insertado(logger, id_ins: int, datos: dict):
    # No se loguea cada insert individual (serían 1 línea/segundo)
    # Solo se usa el contador en log_fin_datalog
    pass


def log_error_insercion(logger, error: str, datos: dict):
    logger.error(
        f"✘ ERROR INSERT tblConsumosCurvas | {error} | "
        f"Datos: SpTemp={datos.get('SpTemperatura')} "
        f"TempReal={datos.get('TempReal')} "
        f"Aire={datos.get('PctAire')} "
        f"Gas={datos.get('PctGas')}"
    )