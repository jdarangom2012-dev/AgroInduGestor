# =============================================================
# sql_writer.py — Inserta en dbo.tblConsumosTueste
#                 via dbo.sp_InsertarConsumosTueste
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

    def insertar(self, d: dict) -> int:
        self._asegurar_conexion()

        sql = (
            f"EXEC {SP_INSERTAR} "
            "@IdOrden=?, @Bache=?, @IdCliente=?, "
            "@PesoCv=?, @PesoCt=?, "
            "@TempDesh=?, @TempRecu=?, @Temp1Crack=?, @TempfinCurva=?, "
            "@TiempoDesh_seg=?, @TiempoRecu_seg=?, "
            "@Tiempo1Crack_seg=?, @TiempofinCurva_seg=?, "
            "@TiempoTueste_seg=?, @TiempoEnfriamiento_seg=?, "
            "@Rendimiento=?, @ConsumoGas=?, @ConsumoKwh=?, "
            "@FechaHoraIni=?, @FechaHoraFin=?, @Nombre=?"
        )

        params = (
            d["IdOrden"],               d["Bache"],
            d["IdCliente"],             d["PesoCv"],
            d["PesoCt"],                d["TempDesh"],
            d["TempRecu"],              d["Temp1Crack"],
            d["TempfinCurva"],          d["TiempoDesh_seg"],
            d["TiempoRecu_seg"],        d["Tiempo1Crack_seg"],
            d["TiempofinCurva_seg"],    d["TiempoTueste_seg"],
            d["TiempoEnfriamiento_seg"],d["Rendimiento"],
            d["ConsumoGas"],            d["ConsumoKwh"],
            d["FechaHoraIni"],          d["FechaHoraFin"],
            d["Nombre"],
        )

        cur = self.conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        self.conn.commit()
        return int(row[0]) if row else -1