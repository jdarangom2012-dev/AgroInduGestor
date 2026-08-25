from django.db import models


class CurvaTueste(models.Model):
    id = models.BigAutoField(db_column='Id', primary_key=True)
    fecha_ingreso = models.DateTimeField(db_column='FechaHora', blank=True, null=True)
    numero_orden = models.IntegerField(db_column='NumeroOrden', blank=True, null=True)
    bache = models.IntegerField(db_column='Batche', blank=True, null=True)
    temp_set_point = models.FloatField(db_column='SpTemperatura', blank=True, null=True)
    temp_tost = models.FloatField(db_column='TempReal', blank=True, null=True)
    porcentaje_aire = models.FloatField(db_column='PctAire', blank=True, null=True)
    porcentaje_gas = models.FloatField(db_column='PctGas', blank=True, null=True)

    class Meta:
        db_table = 'tblConsumosCurvas'

    def __str__(self):
        return f'CurvaTueste {self.id}'


class ConsumoTuestePLC(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)
    numero_orden = models.IntegerField(db_column='NumeroOrden', blank=True, null=True)
    bache = models.IntegerField(db_column='Bache', blank=True, null=True)
    cliente = models.CharField(db_column='Nombre', max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'tblConsumosTueste'
        managed = False
