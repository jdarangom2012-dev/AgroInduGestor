# =============================================================
# config.py — Servicio PLCCurvasTueste
# Lee %M30 cada 1 segundo → tblConsumosCurvas
# =============================================================

# ── PLC ──────────────────────────────────────────────────────
PLC_HOST        = "192.168.0.4"
PLC_PORT        = 502
PLC_UNIT_ID     = 255
POLL_SEG        = 1          # Cada 1 segundo (curva en tiempo real)

# ── Bit disparador ───────────────────────────────────────────
# %M30 → coil 30 (base 0)
# Mientras esté en 1 → guarda una fila por segundo
# Cuando vuelve a 0 → deja de guardar (tueste terminó)
COIL_TRIGGER    = 30

# ── Registros a leer ─────────────────────────────────────────
# %MW80 = HMI_GRAFICO_VAR1 → SP Temperatura (curva referencia)  ###.#
# %MW81 = HMI_GRAFICO_VAR2 → Temperatura real                   ###.#
# %MW82 = HMI_GRAFICO_VAR3 → Porcentaje de aire                 ###.#
# %MW83 = HMI_GRAFICO_VAR4 → Porcentaje de gas                  ###.#
# Los valores vienen con 1 decimal implícito (×10), ej: 1854 = 185.4
REGS_START      = 80
REGS_COUNT      = 4    # MW80, MW81, MW82, MW83

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

SP_INSERTAR = "dbo.spInsertarConsumosCurvas"

# ── Log ──────────────────────────────────────────────────────
LOG_FILE         = r"C:\inetpub\wwwroot\AgroindugestorQA\Servicio\PLCServiceCurvas\logs\plc_curvas_rt.log"
LOG_MAX_BYTES    = 10 * 1024 * 1024  # 10 MB (genera más datos al ser cada segundo)
LOG_BACKUP_COUNT = 5
