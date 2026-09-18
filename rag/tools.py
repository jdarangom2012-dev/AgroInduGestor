from django.db.models import Count, Q, Sum
from django.urls import reverse

from inventario_cafe.models import InventarioCafe
from ordenes.models import Orden
from reportes.services.facturacion import get_facturacion_report_by_id
from seguridad.helpers import tiene_permiso


def _allowed(user, permission_code):
    return bool(
        getattr(user, 'is_superuser', False)
        or tiene_permiso(user, permission_code)
    )


def _forbidden():
    return {'ok': False, 'error': 'El usuario no tiene permiso para consultar esta información.'}


def _find_order(order_number):
    return (
        Orden.objects.select_related('cliente', 'estado_orden')
        .filter(orden=str(order_number).strip())
        .first()
    )


def buscar_orden(user, numero_orden):
    if not _allowed(user, 'ver_orden_produccion'):
        return _forbidden()
    order = _find_order(numero_orden)
    if not order:
        return {'ok': False, 'error': f'No existe la orden {numero_orden}.'}
    return {
        'ok': True,
        'orden': order.orden,
        'cliente': str(order.cliente) if order.cliente else '-',
        'estado': str(order.estado_orden) if order.estado_orden else '-',
        'fecha_inicio': order.fecha_inicio_orden.isoformat() if order.fecha_inicio_orden else None,
        'fecha_entrega': order.fecha_entrega.isoformat() if order.fecha_entrega else None,
        'peso_bruto_kg': order.peso_bruto or 0,
        'peso_neto_kg': order.peso or 0,
        'notas': order.notas or '',
    }


def contar_ordenes_por_estado(user, estado):
    if not _allowed(user, 'ver_orden_produccion'):
        return _forbidden()
    state = str(estado).strip()
    if not state:
        return {'ok': False, 'error': 'Debes indicar el estado de las órdenes.'}
    queryset = Orden.objects.filter(estado_orden__estado_orden__icontains=state)
    return {
        'ok': True,
        'estado_buscado': state,
        'cantidad': queryset.count(),
        'ordenes_recientes': list(
            queryset.order_by('-fecha_inicio_orden', '-id').values_list('orden', flat=True)[:10]
        ),
    }


def consultar_inventario_cliente(user, cliente):
    if not _allowed(user, 'ver_inventario'):
        return _forbidden()
    name = str(cliente).strip()
    if not name:
        return {'ok': False, 'error': 'Debes indicar el cliente que deseas consultar.'}
    client_filter = Q()
    for term in name.split():
        client_filter &= (
            Q(cliente__nombre__icontains=term)
            | Q(cliente__apellidos__icontains=term)
            | Q(cliente__codigo__icontains=term)
        )
    queryset = (
        InventarioCafe.objects.select_related('cliente', 'estado_cafe')
        .filter(client_filter)
        .order_by('-fecha_ingreso', '-id')
    )
    totals = queryset.aggregate(total=Sum('cantidad_existente'), records=Count('id'))
    return {
        'ok': True,
        'cliente_buscado': name,
        'cantidad_existente_total_kg': float(totals['total'] or 0),
        'registros': totals['records'] or 0,
        'detalle': [
            {
                'codigo': item.codigo,
                'descripcion': item.descripcion,
                'estado': str(item.estado_cafe) if item.estado_cafe else '-',
                'cantidad_existente_kg': float(item.cantidad_existente or 0),
            }
            for item in queryset[:10]
        ],
    }


def consultar_procesos_orden(user, numero_orden):
    if not _allowed(user, 'ver_orden_produccion'):
        return _forbidden()
    order = _find_order(numero_orden)
    if not order:
        return {'ok': False, 'error': f'No existe la orden {numero_orden}.'}
    report = get_facturacion_report_by_id(order.id)
    return {
        'ok': True,
        'orden': order.orden,
        'cliente': str(order.cliente) if order.cliente else '-',
        'estado': str(order.estado_orden) if order.estado_orden else '-',
        'procesos': report.get('procesos', {}),
        'etiquetas': report.get('etiquetas', {}),
    }


def generar_reporte(user, numero_orden, report_type):
    if not _allowed(user, 'ver_reportes'):
        return _forbidden()
    order = _find_order(numero_orden)
    if not order:
        return {'ok': False, 'error': f'No existe la orden {numero_orden}.'}

    if report_type == 'facturacion':
        url = reverse('reportes_facturacion_pdf', args=[order.id])
        label = f'Descargar Facturación · Orden {order.orden}'
    else:
        url = reverse('reportes_clientes_pdf', args=[order.id])
        label = f'Descargar Reporte de Cliente · Orden {order.orden}'
    return {
        'ok': True,
        'orden': order.orden,
        'cliente': str(order.cliente) if order.cliente else '-',
        'mensaje': 'El reporte está listo para descargar.',
        'action': {'url': url, 'label': label},
    }


TOOL_DEFINITIONS = [
    {
        'type': 'function',
        'name': 'buscar_documentacion',
        'description': 'Busca información conceptual, técnica o funcional en los documentos de AgroInduGestor.',
        'parameters': {
            'type': 'object',
            'properties': {'pregunta': {'type': 'string'}},
            'required': ['pregunta'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'buscar_orden',
        'description': 'Consulta datos actuales de una orden de producción por su número.',
        'parameters': {
            'type': 'object',
            'properties': {'numero_orden': {'type': 'string'}},
            'required': ['numero_orden'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'contar_ordenes_por_estado',
        'description': 'Cuenta órdenes actuales por estado, por ejemplo Pendiente, En Espera o Completada.',
        'parameters': {
            'type': 'object',
            'properties': {'estado': {'type': 'string'}},
            'required': ['estado'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'consultar_inventario_cliente',
        'description': 'Consulta el inventario actual y la cantidad existente de café asociada a un cliente.',
        'parameters': {
            'type': 'object',
            'properties': {'cliente': {'type': 'string'}},
            'required': ['cliente'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'consultar_procesos_orden',
        'description': 'Consulta los datos actuales de trilla, selección verde, tueste, selección tueste y empaque de una orden.',
        'parameters': {
            'type': 'object',
            'properties': {'numero_orden': {'type': 'string'}},
            'required': ['numero_orden'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'generar_reporte_facturacion',
        'description': 'Prepara el PDF existente del reporte de facturación para una orden.',
        'parameters': {
            'type': 'object',
            'properties': {'numero_orden': {'type': 'string'}},
            'required': ['numero_orden'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'generar_reporte_cliente',
        'description': 'Prepara el PDF existente del reporte de clientes para una orden.',
        'parameters': {
            'type': 'object',
            'properties': {'numero_orden': {'type': 'string'}},
            'required': ['numero_orden'],
            'additionalProperties': False,
        },
        'strict': True,
    },
]
