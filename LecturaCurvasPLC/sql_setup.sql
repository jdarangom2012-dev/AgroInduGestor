-- =============================================================
-- sql_setup.sql — tblConsumosCurvas + spInsertarConsumosCurvas
-- Curva de tueste en tiempo real — 1 fila por segundo
-- =============================================================

USE TU_BASE_DATOS;   -- ← Cambia por tu base de datos
GO

-- =============================================================
-- 1. TABLA
-- =============================================================
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'tblConsumosCurvas')
BEGIN
    CREATE TABLE dbo.tblConsumosCurvas (
        Id              BIGINT IDENTITY(1,1) PRIMARY KEY,
        FechaHora       DATETIME2(0)  NOT NULL DEFAULT SYSDATETIME(),
        SpTemperatura   FLOAT         NULL,   -- %MW80  SP Temp curva referencia (°C ×0.1)
        TempReal        FLOAT         NULL,   -- %MW81  Temperatura real tambor  (°C ×0.1)
        PctAire         FLOAT         NULL,   -- %MW82  Porcentaje apertura aire (% ×0.1)
        PctGas          FLOAT         NULL,   -- %MW83  Porcentaje apertura gas  (% ×0.1)
    );

    CREATE INDEX IX_ConsumosCurvas_FechaHora
        ON dbo.tblConsumosCurvas (FechaHora DESC);

    PRINT '✔ Tabla dbo.tblConsumosCurvas creada.';
END
ELSE
    PRINT 'Tabla dbo.tblConsumosCurvas ya existe.';
GO

-- =============================================================
-- 2. STORED PROCEDURE
-- =============================================================
CREATE OR ALTER PROCEDURE dbo.spInsertarConsumosCurvas
(
    @SpTemperatura  FLOAT = NULL,
    @TempReal       FLOAT = NULL,
    @PctAire        FLOAT = NULL,
    @PctGas         FLOAT = NULL
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        INSERT INTO dbo.tblConsumosCurvas (
            SpTemperatura, TempReal, PctAire, PctGas
        )
        VALUES (
            @SpTemperatura, @TempReal, @PctAire, @PctGas
        );

        -- Retorna el Id para el log de Python
        SELECT SCOPE_IDENTITY() AS IdInsertado;
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END;
GO

PRINT '✔ dbo.spInsertarConsumosCurvas creado/actualizado OK';
GO

-- =============================================================
-- CONSULTAS ÚTILES
-- =============================================================

-- Ver la curva del último tueste (últimos 30 min)
-- SELECT FechaHora, SpTemperatura, TempReal, PctAire, PctGas
-- FROM dbo.tblConsumosCurvas
-- WHERE FechaHora >= DATEADD(MINUTE, -30, SYSDATETIME())
-- ORDER BY FechaHora ASC;

-- Total de registros por hora hoy
-- SELECT
--     DATEPART(HOUR, FechaHora) AS Hora,
--     COUNT(*) AS Registros,
--     AVG(TempReal) AS TempReal_Prom,
--     AVG(SpTemperatura) AS SpTemp_Prom
-- FROM dbo.tblConsumosCurvas
-- WHERE CAST(FechaHora AS DATE) = CAST(SYSDATETIME() AS DATE)
-- GROUP BY DATEPART(HOUR, FechaHora)
-- ORDER BY Hora;
