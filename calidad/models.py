import json

from django.db import models


class Calidad(models.Model):
    id = models.BigAutoField(db_column='Id', primary_key=True)
    fecha_ingreso = models.DateTimeField(db_column='FechaIngreso', auto_now_add=True)
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, db_column='IdCliente')
    fecha_recibido = models.DateField(db_column='FechaRecibido', blank=True, null=True)
    sencilla = models.BooleanField(db_column='Sencilla', default=False)
    q_grader = models.BooleanField(db_column='QGrader', default=False)
    muestra_numero = models.CharField(db_column='MuestraNumero', max_length=30, blank=True)
    orden = models.CharField(db_column='Orden', max_length=50)
    variedad = models.CharField(db_column='Variedad', max_length=80, blank=True)
    proceso = models.ForeignKey('proceso_inven_cafe.ProcesoInvenCafe', on_delete=models.PROTECT, db_column='IdProceso')
    origen = models.CharField(db_column='Origen', max_length=80, blank=True)
    altura = models.FloatField(db_column='Altura', blank=True, null=True)
    peso_pergamino = models.FloatField(db_column='PesoPergamino', blank=True, null=True)
    humedad = models.FloatField(db_column='Humedad', blank=True, null=True)
    densidad = models.FloatField(db_column='Densidad', blank=True, null=True)
    peso_verde = models.FloatField(db_column='PesoVerde', blank=True, null=True)
    peso_excelsio = models.FloatField(db_column='PesoExcelsio', blank=True, null=True)
    peso_defecto = models.FloatField(db_column='PesoDefecto', blank=True, null=True)
    factor = models.FloatField(db_column='Factor', blank=True, null=True)
    notas = models.TextField(db_column='Notas', blank=True)
    tostion_json = models.TextField(db_column='Tostion', default='[]')
    peso_tostado = models.FloatField(db_column='PesoTostado', blank=True, null=True)
    observaciones = models.TextField(db_column='Observaciones', blank=True)

    class Meta:
        db_table = 'tblcalidad'
        ordering = ['-fecha_ingreso', '-id']

    def __str__(self):
        return f'{self.orden} - {self.cliente}'

    @property
    def lecturas_tostion(self):
        try:
            return json.loads(self.tostion_json or '[]')
        except (TypeError, ValueError):
            return []
