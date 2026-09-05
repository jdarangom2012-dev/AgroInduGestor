from django.db.models import Avg, Sum

from empaques.models import DetalleEmpaque, Empaque
from ordenes.models import DetalleEmpaqueOrden, Orden
from ordenes_seleccion_verde.models import OrdenSeleccionVerde
from ordenes_trilla.models import OrdenTrilla
from seleccion_tueste.models import SeleccionTueste
from tueste.models import DetalleTueste, Tueste


ESTADO_COMPLETADA = "Completada"


def _sum_value(value):
    return float(value or 0)


def _process_applies(orden, field_name):
    return bool(getattr(orden, field_name, False))


def _completed_task_filter(prefix="estado_tareas"):
    return {f"{prefix}__estado_tareas__iexact": ESTADO_COMPLETADA}


def _completed_order_state_filter(prefix="estado_tareas"):
    return {f"{prefix}__estado_orden__iexact": ESTADO_COMPLETADA}


def _sum_fields(queryset, **field_map):
    totals = queryset.aggregate(**{key: Sum(field_name) for key, field_name in field_map.items()})
    return {key: _sum_value(value) for key, value in totals.items()}


def get_available_orders():
    return (
        Orden.objects.select_related("cliente", "estado_orden")
        .order_by("-fecha_inicio_orden", "-id")
        .only("id", "orden", "fecha_inicio_orden", "cliente__nombre", "cliente__apellidos", "estado_orden__estado_orden")
    )


def get_facturacion_report(order_value):
    order_value = (order_value or "").strip()
    if not order_value:
        return {"orden": None, "not_found": False, "selected_order": ""}

    orden = _get_order_by_number(order_value)
    if orden is None:
        return {"orden": None, "not_found": True, "selected_order": order_value}

    return build_facturacion_context(orden, selected_order=order_value)


def get_facturacion_report_by_id(orden_id):
    try:
        orden = _base_order_queryset().get(pk=orden_id)
    except Orden.DoesNotExist:
        return {"orden": None, "not_found": True, "selected_order": ""}

    return build_facturacion_context(orden, selected_order=orden.orden or "")


def _base_order_queryset():
    return Orden.objects.select_related("cliente", "estado_orden").prefetch_related(
        "detalles_empaque__empaque_cafe",
        "detalles_empaque__tamano_empaque",
    )


def _get_order_by_number(order_value):
    try:
        return _base_order_queryset().get(orden=order_value)
    except Orden.DoesNotExist:
        return None


def build_facturacion_context(orden, selected_order=""):
    trilla = build_trilla_section(orden)
    seleccion_verde = build_seleccion_verde_section(orden, trilla)
    tueste = build_tueste_section(orden)
    seleccion_tostado = build_seleccion_tostado_section(orden)
    empaque = build_empaque_section(orden)
    etiquetas = build_etiquetas_section(orden)

    return {
        "orden": orden,
        "not_found": False,
        "selected_order": selected_order,
        "procesos": {
            "trilla": trilla,
            "seleccion_verde": seleccion_verde,
            "tueste": tueste,
            "seleccion_tostado": seleccion_tostado,
            "empaque": empaque,
        },
        "etiquetas": etiquetas,
        "observaciones": build_observaciones_section(orden),
    }


def build_trilla_section(orden):
    if not _process_applies(orden, "trilla"):
        return {"aplica": False, "entrada": 0, "salida": 0}

    totals = _sum_fields(
        OrdenTrilla.objects.filter(orden__cliente_id=getattr(orden, "cliente_id", None)),
        entrada="peso_cafe_bruto",
        salida="peso_cafe_verde",
    )
    rendimiento = (totals["salida"] / totals["entrada"] * 100) if totals["entrada"] else 0
    return {
        "aplica": True,
        "entrada": totals["entrada"],
        "salida": totals["salida"],
        "rendimiento": rendimiento,
    }


def build_seleccion_verde_section(orden, trilla_section=None):
    if not _process_applies(orden, "selec_cafe_verde"):
        return {
            "aplica": False,
            "entrada": 0,
            "total_de_grupo": 0,
            "peso_aceptado": 0,
            "humedad": 0,
            "densidad": 0,
        }

    trilla_section = trilla_section or build_trilla_section(orden)
    registros_orden = OrdenSeleccionVerde.objects.filter(orden=orden)
    totals = _sum_fields(
        registros_orden,
        peso_grupo1="peso_grupo1",
        peso_grupo2="peso_grupo2",
        peso_grupo3="peso_grupo3",
        peso_grupo4="peso_grupo4",
        peso_grupo5="peso_grupo5",
        peso_grupo_ripio="peso_grupo_ripio",
        peso_cat_ripio="peso_cat_ripio",
        peso_cat_balsos="peso_cat_balsos",
        peso_cat_grupo1="peso_cat_grupo1",
        peso_cat_grupo2="peso_cat_grupo2",
        peso_aceptado="peso_aceptado",
    )
    mediciones_cliente = OrdenSeleccionVerde.objects.filter(
        orden__cliente_id=getattr(orden, "cliente_id", None),
    )
    mediciones = mediciones_cliente.filter(**_completed_task_filter()).aggregate(
        humedad=Avg("humedad"),
        densidad=Avg("densidad"),
    )
    if mediciones["humedad"] is None or mediciones["densidad"] is None:
        mediciones_disponibles = mediciones_cliente.aggregate(
            humedad=Avg("humedad"),
            densidad=Avg("densidad"),
        )
        if mediciones["humedad"] is None:
            mediciones["humedad"] = mediciones_disponibles["humedad"]
        if mediciones["densidad"] is None:
            mediciones["densidad"] = mediciones_disponibles["densidad"]
    total_de_grupo = sum(
        totals[field_name]
        for field_name in (
            "peso_cat_ripio",
            "peso_cat_balsos",
            "peso_cat_grupo1",
            "peso_cat_grupo2",
        )
    )
    cataciones = {
        "ripio": {
            "seleccionada": registros_orden.filter(catacion_ripio=True).exists(),
            "peso": _sum_fields(registros_orden.filter(catacion_ripio=True), peso="peso_cat_ripio")["peso"],
        },
        "balsos": {
            "seleccionada": registros_orden.filter(catacion_balsos=True).exists(),
            "peso": _sum_fields(registros_orden.filter(catacion_balsos=True), peso="peso_cat_balsos")["peso"],
        },
        "grupo1": {
            "seleccionada": registros_orden.filter(catacion_grupo1=True).exists(),
            "peso": _sum_fields(registros_orden.filter(catacion_grupo1=True), peso="peso_cat_grupo1")["peso"],
        },
        "grupo2": {
            "seleccionada": registros_orden.filter(catacion_grupo2=True).exists(),
            "peso": _sum_fields(registros_orden.filter(catacion_grupo2=True), peso="peso_cat_grupo2")["peso"],
        },
    }
    return {
        "aplica": True,
        "entrada": _sum_value(trilla_section.get("salida")),
        "total_de_grupo": total_de_grupo,
        "peso_aceptado": totals["peso_aceptado"],
        "humedad": _sum_value(mediciones["humedad"]),
        "densidad": _sum_value(mediciones["densidad"]),
        "mallas": {
            "grupo1": totals["peso_grupo1"],
            "grupo2": totals["peso_grupo2"],
            "grupo3": totals["peso_grupo3"],
            "grupo4": totals["peso_grupo4"],
            "grupo5": totals["peso_grupo5"],
            "ripio": totals["peso_grupo_ripio"],
        },
        "cataciones": cataciones,
    }


def build_tueste_section(orden):
    if not _process_applies(orden, "tueste_flag"):
        return {"aplica": False, "entrada": 0, "salida": 0, "detalle_batches": []}

    registros = Tueste.objects.filter(orden=orden, **_completed_task_filter())
    totals = _sum_fields(
        registros,
        entrada="peso_cafe_vede_total",
        salida="peso_cafe_tostado_total",
    )
    niveles = list(
        registros.exclude(nivel_tueste__nivel_tueste__isnull=True)
        .exclude(nivel_tueste__nivel_tueste="")
        .values_list("nivel_tueste__nivel_tueste", flat=True)
        .distinct()
    )
    detalle_batches = list(
        DetalleTueste.objects.filter(tueste__in=registros)
        .select_related("estado_orden", "nivel_tueste")
        .order_by("tueste_id", "numero_batch", "id")
        .values(
            "tueste_id",
            "numero_batch",
            "estado_orden__estado_orden",
            "nivel_tueste__nivel_tueste",
            "kilos_verde",
            "kilos_tostado",
            "observaciones",
        )
    )
    rendimiento = (totals["salida"] / totals["entrada"] * 100) if totals["entrada"] else 0
    return {
        "aplica": True,
        "entrada": totals["entrada"],
        "salida": totals["salida"],
        "rendimiento": rendimiento,
        "nivel_tueste": ", ".join(niveles) if niveles else "-",
        "detalle_batches": detalle_batches,
    }


def build_seleccion_tostado_section(orden):
    if not _process_applies(orden, "selec_cafe_tostado"):
        return {
            "aplica": False,
            "peso_quaker": 0,
            "peso_grupo1": 0,
            "peso_grupo2": 0,
            "peso_grupo3": 0,
            "total_registrado": 0,
        }

    seleccion_tueste = _sum_fields(
        SeleccionTueste.objects.filter(orden=orden),
        peso_quaker="peso_quaker",
        peso_grupo1="peso_grupo1",
        peso_grupo2="peso_grupo2",
        peso_grupo3="peso_grupo3",
    )

    totals = {
        key: seleccion_tueste[key]
        for key in ("peso_quaker", "peso_grupo1", "peso_grupo2", "peso_grupo3")
    }
    totals["total_registrado"] = sum(totals.values())

    return {
        "aplica": True,
        **totals,
    }


def build_empaque_section(orden):
    if not _process_applies(orden, "empaque_flag"):
        return {
            "aplica": False,
            "bolsas_empacadas": [],
            "detalle_empaque": [],
            "empaques_suministrados": [],
            "suministro_cliente": bool(getattr(orden, "trabajo_empaque", False)),
            "cantidad_bolsas_empacadas": 0,
            "total_paquetes": 0,
        }

    empaques_qs = Empaque.objects.filter(orden=orden)
    empaques = empaques_qs.values("id")
    bolsas_empacadas = list(
        DetalleEmpaque.objects.filter(empaque_id__in=empaques)
        .values("empaque_cafe__empaque_cafe", "tamano_empaque__tamano_empaque", "suministro")
        .annotate(cantidad=Sum("empacado"))
        .order_by("empaque_cafe__empaque_cafe", "tamano_empaque__tamano_empaque", "suministro")
    )
    detalle_empaque = list(
        DetalleEmpaque.objects.filter(empaque_id__in=empaques)
        .values(
            "empaque_cafe__empaque_cafe",
            "tamano_empaque__tamano_empaque",
            "pedido",
            "empacado",
        )
        .order_by("empaque_id", "id")
    )

    suministro_cliente = bool(getattr(orden, "trabajo_empaque", False))
    empaques_suministrados = []
    if suministro_cliente:
        empaques_suministrados = list(
            DetalleEmpaqueOrden.objects.filter(orden=orden)
            .values("empaque_cafe__empaque_cafe", "tamano_empaque__tamano_empaque")
            .annotate(cantidad=Sum("cantidad"))
            .order_by("empaque_cafe__empaque_cafe", "tamano_empaque__tamano_empaque")
        )

    totals = _sum_fields(
        empaques_qs,
        cantidad_bolsas_empacadas="cant_empacada",
        total_paquetes="total_paquetes",
    )

    return {
        "aplica": True,
        "bolsas_empacadas": bolsas_empacadas,
        "detalle_empaque": detalle_empaque,
        "suministro_cliente": suministro_cliente,
        "empaques_suministrados": empaques_suministrados,
        "cantidad_bolsas_empacadas": totals["cantidad_bolsas_empacadas"],
        "total_paquetes": totals["total_paquetes"],
    }


def build_etiquetas_section(orden):
    empaques_con_etiquetas = Empaque.objects.filter(
        orden=orden,
        lleva_etiquetas=True,
    )
    etiquetas_cliente = _sum_value(
        Empaque.objects.filter(orden=orden).aggregate(total=Sum("emp_clientes")).get("total")
    )
    invima = bool(getattr(orden, "etiqueta_invima", False))
    etiquetas_invima = _sum_value(
        empaques_con_etiquetas.aggregate(total=Sum("cant_etiquetas")).get("total")
    ) if invima else 0
    total_etiquetas = etiquetas_cliente + etiquetas_invima
    return {
        "cliente": etiquetas_cliente,
        "invima": etiquetas_invima,
        "total": total_etiquetas,
        "requiere_invima": invima,
    }


def build_observaciones_section(orden):
    observaciones = []
    if getattr(orden, "notas", None):
        observaciones.append({"origen": "Orden de Producción", "texto": orden.notas})

    sources = [
        ("Trilla", OrdenTrilla.objects.filter(orden=orden, **_completed_task_filter())),
        ("Selección Verde", OrdenSeleccionVerde.objects.filter(orden=orden, **_completed_task_filter())),
        ("Tueste", Tueste.objects.filter(orden=orden, **_completed_task_filter())),
        ("Selección Tueste", SeleccionTueste.objects.filter(orden=orden)),
        ("Empaque", Empaque.objects.filter(orden=orden, **_completed_task_filter())),
    ]

    for origen, queryset in sources:
        for nota in queryset.exclude(notas__isnull=True).exclude(notas="").values_list("notas", flat=True):
            observaciones.append({"origen": origen, "texto": nota})

    for nota in (
        DetalleTueste.objects.filter(tueste__orden=orden, **_completed_task_filter("tueste__estado_tareas"))
        .exclude(observaciones__isnull=True)
        .exclude(observaciones="")
        .values_list("observaciones", flat=True)
    ):
        observaciones.append({"origen": "Detalle Tueste", "texto": nota})

    return observaciones
