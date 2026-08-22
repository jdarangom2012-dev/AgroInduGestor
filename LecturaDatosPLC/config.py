# =============================================================
# config.py — Configuración centralizada
# PLC Modicon M221 TM221CE40R → SQL Server
# =============================================================

# ── PLC ──────────────────────────────────────────────────────
PLC_HOST        = "192.168.0.4"
PLC_PORT        = 502
PLC_UNIT_ID     = 1
POLL_SEG        = 2          # Cada cuántos segundos se lee %M93

# ── Bit disparador ───────────────────────────────────────────
# %M93 → coil número 93 (base 0).
# Cuando el PLC lo pone en 1, Python lee todo y ejecuta el SP.
# Después de guardar, Python resetea el coil a 0.
COIL_TRIGGER        = 93   # %M93 — PLC activa cuando orden completa
                           #         Python lo apaga cuando INSERT es exitoso

# ── SQL Server ───────────────────────────────────────────────
SQL_CONN = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=WIN-BJ6FABBG7OK\TLCMAIN01;"          # ← igual que el primer servicio
    "DATABASE=dbTostadoraCentral;"
    "UID=sa;"
    "PWD=Tostadora2026*;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=10;"
)
# Un único SP que inserta en dbo.tblConsumosTostion
SP_INSERTAR = "dbo.sp_InsertarConsumosTueste"

# ── Log ──────────────────────────────────────────────────────
LOG_FILE         = r"C:\PLCService\logs\plc_curvas.log"
LOG_MAX_BYTES    = 5 * 1024 * 1024   # 5 MB por archivo
LOG_BACKUP_COUNT = 5                  # Mantener 5 rotaciones