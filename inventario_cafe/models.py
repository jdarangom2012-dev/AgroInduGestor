import re

from django.db import models
from django.utils import timezone


class InventarioCafe(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)
    cliente = models.ForeignKey('clientes.Cliente', models.SET_NULL, db_column='IdClientes', blank=True, null=True)
    estado_cafe = models.ForeignKey('estado_cafe.EstadoCafe', models.SET_NULL, db_column='IdEstadoCafe', blank=True, null=True)
    proceso_inven_cafe = models.ForeignKey('proceso_inven_cafe.ProcesoInvenCafe', models.SET_NULL, db_column='IdProcesoInvenCafe', blank=True, null=True)
    variendad_inven_cafe = models.ForeignKey('variedad_cafe.VariedadCafe', models.SET_NULL, db_column='IdVariendadInvenCafe', blank=True, null=True)
    origen = models.ForeignKey('origen_cafe.OrigenCafe', models.SET_NULL, db_column='IdOrigen', blank=True, null=True)
    empaquecafe = models.ForeignKey('cafe_empaque.CafeEmpaque', models.SET_NULL, db_column='IdEmpaqueCafe', blank=True, null=True)
    fecha_ingreso = models.DateTimeField(db_column='FechaIngreso', blank=True, null=True)
    codigo = models.CharField(db_column='Codigo', max_length=26, blank=True, null=True)
    descripcion = models.CharField(db_column='Descripcion', max_length=50, blank=True, null=True)
    cantidad = models.FloatField(db_column='Cantidad', blank=True, null=True)
    cantidad_existente = models.FloatField(db_column='CantidadExistente', default=0)
    kilos_ingresar = models.FloatField(db_column='KilosIngresar', blank=True, null=True)
    kilos_sacar = models.FloatField(db_column='KilosSacar', blank=True, null=True)
    notas = models.TextField(db_column='Notas', blank=True, null=True)
    sacos = models.IntegerField(db_column='Sacos', blank=True, null=True)
    cantidad_bolsas_emp = models.IntegerField(db_column='CantidadBolsasEmp', blank=True, null=True)
    cantidad_paquetes = models.IntegerField(db_column='CantidadPaquetes', blank=True, null=True)
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at', blank=True, null=True)

    class Meta:
        db_table = 'tblInventarioCafe'
        indexes = [
            models.Index(fields=['codigo'], name='idx_inv_codigo'),
            models.Index(fields=['cliente'], name='idx_inv_cliente'),
            models.Index(fields=['estado_cafe'], name='idx_inv_estado_cafe'),
        ]

    def __str__(self):
        return f'InventarioCafe {self.id}'

    @staticmethod
    def _build_codigo_segment(value, length):
        if not value:
            return ''
        normalized = re.sub(r'[\s-]+', '', str(value).strip())
        if not normalized:
            return ''
        normalized = normalized[:length]
        return normalized[:1].upper() + normalized[1:].lower()

    def build_codigo(self):
        parts = [
            self._build_codigo_segment(getattr(self.cliente, 'nombre', None), 6),
            self._build_codigo_segment(getattr(self.estado_cafe, 'estado_cafe', None), 3),
            self._build_codigo_segment(getattr(self.variendad_inven_cafe, 'variedad_cafe', None), 3),
            self._build_codigo_segment(getattr(self.proceso_inven_cafe, 'proceso_inven_cafe', None), 3),
            self._build_codigo_segment(getattr(self.origen, 'origen', None), 3),
            timezone.localdate().strftime('%Y%m%d'),
        ]
        return ''.join(parts)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.cantidad_existente = round((
                (self.cantidad or 0)
                + (self.kilos_ingresar or 0)
                - (self.kilos_sacar or 0)
            ), 2)
        self.codigo = self.build_codigo()
        super().save(*args, **kwargs)
