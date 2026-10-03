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


class AnalisisSensorial(models.Model):
    id = models.BigAutoField(db_column='Id', primary_key=True)
    fecha_ingreso = models.DateTimeField(db_column='FechaIngreso', auto_now_add=True)
    nombre = models.CharField(db_column='Nombre', max_length=120)
    fecha = models.DateField(db_column='Fecha')
    objetivo = models.CharField(db_column='Objetivo', max_length=200, blank=True)
    muestra_numero = models.CharField(db_column='MuestraNumero', max_length=60)
    nivel_tueste = models.PositiveSmallIntegerField(db_column='NivelTueste', blank=True, null=True)

    intensidad_fragancia = models.DecimalField(db_column='IntensidadFragancia', max_digits=4, decimal_places=1, blank=True, null=True)
    intensidad_aroma = models.DecimalField(db_column='IntensidadAroma', max_digits=4, decimal_places=1, blank=True, null=True)
    descriptores_fragancia_aroma = models.TextField(db_column='DescriptoresFraganciaAroma', default='[]', blank=True)
    notas_fragancia_aroma = models.TextField(db_column='NotasFraganciaAroma', blank=True)

    intensidad_sabor = models.DecimalField(db_column='IntensidadSabor', max_digits=4, decimal_places=1, blank=True, null=True)
    intensidad_sabor_residual = models.DecimalField(db_column='IntensidadSaborResidual', max_digits=4, decimal_places=1, blank=True, null=True)
    descriptores_sabor = models.TextField(db_column='DescriptoresSabor', default='[]', blank=True)
    gustos_predominantes = models.TextField(db_column='GustosPredominantes', default='[]', blank=True)
    notas_sabor = models.TextField(db_column='NotasSabor', blank=True)

    intensidad_acidez = models.DecimalField(db_column='IntensidadAcidez', max_digits=4, decimal_places=1, blank=True, null=True)
    notas_acidez = models.TextField(db_column='NotasAcidez', blank=True)
    intensidad_dulzor = models.DecimalField(db_column='IntensidadDulzor', max_digits=4, decimal_places=1, blank=True, null=True)
    notas_dulzor = models.TextField(db_column='NotasDulzor', blank=True)
    intensidad_sensacion_boca = models.DecimalField(db_column='IntensidadSensacionBoca', max_digits=4, decimal_places=1, blank=True, null=True)
    sensaciones_boca = models.TextField(db_column='SensacionesBoca', default='[]', blank=True)
    notas_sensacion_boca = models.TextField(db_column='NotasSensacionBoca', blank=True)
    notas_extrinseca = models.TextField(db_column='NotasExtrinseca', blank=True)

    calidad_fragancia = models.PositiveSmallIntegerField(db_column='CalidadFragancia', blank=True, null=True)
    calidad_aroma = models.PositiveSmallIntegerField(db_column='CalidadAroma', blank=True, null=True)
    notas_afectiva_fragancia_aroma = models.TextField(db_column='NotasAfectivaFraganciaAroma', blank=True)
    calidad_sabor = models.PositiveSmallIntegerField(db_column='CalidadSabor', blank=True, null=True)
    calidad_sabor_residual = models.PositiveSmallIntegerField(db_column='CalidadSaborResidual', blank=True, null=True)
    notas_afectiva_sabor = models.TextField(db_column='NotasAfectivaSabor', blank=True)
    calidad_acidez = models.PositiveSmallIntegerField(db_column='CalidadAcidez', blank=True, null=True)
    notas_afectiva_acidez = models.TextField(db_column='NotasAfectivaAcidez', blank=True)
    calidad_dulzor = models.PositiveSmallIntegerField(db_column='CalidadDulzor', blank=True, null=True)
    notas_afectiva_dulzor = models.TextField(db_column='NotasAfectivaDulzor', blank=True)
    calidad_sensacion_boca = models.PositiveSmallIntegerField(db_column='CalidadSensacionBoca', blank=True, null=True)
    notas_afectiva_sensacion_boca = models.TextField(db_column='NotasAfectivaSensacionBoca', blank=True)
    impresion_global = models.PositiveSmallIntegerField(db_column='ImpresionGlobal', blank=True, null=True)
    notas_impresion_global = models.TextField(db_column='NotasImpresionGlobal', blank=True)
    puntaje_total = models.DecimalField(db_column='PuntajeTotal', max_digits=6, decimal_places=2, blank=True, null=True)
    tazas_no_uniformes = models.PositiveSmallIntegerField(db_column='TazasNoUniformes', default=0)
    tazas_defectuosas = models.PositiveSmallIntegerField(db_column='TazasDefectuosas', default=0)
    defectos_haberlo = models.TextField(db_column='DefectosHaberlo', default='[]', blank=True)

    class Meta:
        db_table = 'tblAnalisisSensorial'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.muestra_numero} - {self.nombre}'

    @staticmethod
    def _lista_json(valor):
        try:
            resultado = json.loads(valor or '[]')
            return resultado if isinstance(resultado, list) else []
        except (TypeError, ValueError):
            return []

    @property
    def lista_descriptores_fragancia_aroma(self):
        return self._lista_json(self.descriptores_fragancia_aroma)

    @property
    def lista_descriptores_sabor(self):
        return self._lista_json(self.descriptores_sabor)

    @property
    def lista_gustos_predominantes(self):
        return self._lista_json(self.gustos_predominantes)

    @property
    def lista_sensaciones_boca(self):
        return self._lista_json(self.sensaciones_boca)

    @property
    def lista_defectos_haberlo(self):
        return self._lista_json(self.defectos_haberlo)
