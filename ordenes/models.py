from django.db import models
from django.core.exceptions import ObjectDoesNotExist


class Orden(models.Model):
    id_empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.SET_NULL,
        db_column='IdEmpleado',
        null=True,
        blank=True
    )
    sacos_entero = models.IntegerField(db_column='SacosEntero', null=True, blank=True, help_text="Número de sacos enteros procesados")
    peso_bruto = models.FloatField(db_column='PesoBruto', null=True, blank=True, help_text="Peso bruto total en kilogramos")
    peso = models.FloatField(db_column='Peso', null=True, blank=True, help_text="Peso neto total en kilogramos")
    trabajo_empaque = models.BooleanField(db_column='TrabajoEmpaque', default=False, help_text="Indica si el proceso incluye empaque manual")
    etiqueta_invima = models.BooleanField(db_column='EtiquetaInvima', default=False, help_text="Indica si requiere etiqueta Invima en el empaque")
    id = models.AutoField(db_column='Id', primary_key=True)
    cliente = models.ForeignKey('clientes.Cliente', models.SET_NULL, db_column='IdClientes', blank=True, null=True)
    variedad_cafe = models.ForeignKey(
        'variedad_cafe.VariedadCafe',
        on_delete=models.SET_NULL,
        db_column='IdVaridadCafe',
        blank=True,
        null=True
    )
    proceso_inventario_cafe = models.ForeignKey(
        'proceso_inven_cafe.ProcesoInvenCafe',
        on_delete=models.SET_NULL,
        db_column='IdProcesoInvenCafe',
        blank=True,
        null=True
    )
    empaque_cafe = models.ForeignKey('cafe_empaque.CafeEmpaque', models.SET_NULL, db_column='IdEmpaque', blank=True, null=True)
    tamano_empaque = models.ForeignKey('tamano_empaque.TamanoEmpaque', models.SET_NULL, db_column='IdTamanoEmpaque', blank=True, null=True)
    orden = models.CharField(db_column='Orden', max_length=16, blank=True, null=True, unique=True)
    id_inven_cafe = models.ForeignKey(
        'inventario_cafe.InventarioCafe',
        on_delete=models.CASCADE,
        db_column='IdInvenCafe',
        blank=True,
        null=True
    )
    inventario_descontado = models.BooleanField(
        db_column='InventarioDescontado',
        default=False,
        editable=False,
    )
    estado_orden = models.ForeignKey('estado_ordenes.EstadoOrden', models.SET_NULL, db_column='IdEstadoOrden', blank=True, null=True)
    fecha_ingreso = models.DateTimeField(db_column='FechaIngreso', blank=True, null=True)
    fecha_inicio_orden = models.DateTimeField(db_column='FechaIncioOrden', blank=True, null=True)
    fecha_entrega = models.DateTimeField(db_column='FechaEntrega', blank=True, null=True)
    notas = models.CharField(db_column='Notas', max_length=500, blank=True, null=True)
    trilla = models.BooleanField(db_column='Trilla', blank=True, null=True)
    selec_cafe_verde = models.BooleanField(db_column='SelecCafeVerde', blank=True, null=True)
    tueste_flag = models.BooleanField(db_column='Tueste', blank=True, null=True)
    selec_cafe_tostado = models.BooleanField(db_column='SelecCafeTostado', blank=True, null=True)
    molienda_flag = models.BooleanField(db_column='Molienda', blank=True, null=True)
    empaque_flag = models.BooleanField(db_column='Empaque', blank=True, null=True)
    conf_trilla = models.BooleanField(db_column='ConfTrilla', blank=True, null=True)
    conf_sel_verde = models.BooleanField(db_column='ConfSelVerde', blank=True, null=True)
    conf_tueste = models.BooleanField(db_column='ConfTueste', blank=True, null=True)
    conf_sel_tostado = models.BooleanField(db_column='ConfSelTostado', blank=True, null=True, default=False)
    conf_molienda = models.BooleanField(db_column='ConfMolienda', blank=True, null=True)
    conf_empaque = models.BooleanField(db_column='ConfEmpaque', blank=True, null=True)
    prioridad = models.IntegerField(db_column='Prioridad', blank=True, null=True)
    created_at = models.DateTimeField(db_column='created_at', auto_now_add=True)
    updated_at = models.DateTimeField(db_column='updated_at', blank=True, null=True)

    class Meta:
        db_table = 'tblOrdenes'
        indexes = [
            models.Index(fields=['fecha_inicio_orden'], name='idx_orden_fecha'),
            models.Index(fields=['cliente'], name='idx_orden_cliente'),
            models.Index(fields=['estado_orden'], name='idx_orden_estado'),
        ]

    def __str__(self):
        return self.orden or ""


class DetalleEmpaqueOrden(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)
    orden = models.ForeignKey(
        'ordenes.Orden',
        on_delete=models.CASCADE,
        db_column='IdOrden',
        related_name='detalles_empaque',
    )
    empaque_cafe = models.ForeignKey(
        'cafe_empaque.CafeEmpaque',
        on_delete=models.SET_NULL,
        db_column='IdEmpaqueCafe',
        null=True,
        blank=True,
    )
    tamano_empaque = models.ForeignKey(
        'tamano_empaque.TamanoEmpaque',
        on_delete=models.SET_NULL,
        db_column='IdTamanoEmpaque',
        null=True,
        blank=True,
    )
    cantidad = models.PositiveIntegerField(db_column='Cantidad', null=True, blank=True)

    class Meta:
        db_table = 'tblDetalleEmpaqueOrden'
        ordering = ['id']

    def __str__(self):
        return f'DetalleEmpaqueOrden {self.id or "nuevo"}'
