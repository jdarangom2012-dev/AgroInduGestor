# =============================================================
# sql_writer.py — Inserta en dbo.tblConsumosCurvas
#                 via dbo.spInsertarConsumosCurvas
# =============================================================
from typing import Optional
import pyodbc
from config import SQL_CONN, SP_INSERTAR


class SQLWriter:

    def __init__(self):
        self.conn: Optional[pyodbc.Connection] = None

    def conectar(self) -> bool:
        try:
            self.conn = pyodbc.connect(SQL_CONN, autocommit=False)
            return True
        except pyodbc.Error as e:
            raise ConnectionError(f"Error conectando a SQL Server: {e}")

    def desconectar(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

    def _asegurar_conexion(self):
        try:
            if self.conn:
                self.conn.cursor().execute("SELECT 1")
                return
        except Exception:
            pass
        self.conectar()

    def insertar(self, datos: dict) -> int:
        """
        Ejecuta spInsertarConsumosCurvas.
        Parámetros:
            @IdOrden        int   — %MW500
            @Bache          int   — %MW501
            @SpTemperatura  float — %MW80
            @TempReal       float — %MW81
            @PctAire        float — %MW82
            @PctGas         float — %MW83
        """
        self._asegurar_conexion()

        sql = (
            f"EXEC {SP_INSERTAR} "
            "@NumeroOrden=?, @Batche=?, "
            "@SpTemperatura=?, @TempReal=?, @PctAire=?, @PctGas=?"
        )
        params = (
            datos["IdOrden"],
            datos["Bache"],
            datos["SpTemperatura"],
            datos["TempReal"],
            datos["PctAire"],
            datos["PctGas"],
        )

        cur = self.conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        self.conn.commit()
        return int(row[0]) if row else -1