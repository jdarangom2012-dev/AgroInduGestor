from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.http import Http404, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render

from ordenes.models import Orden
from inventario_cafe.models import InventarioCafe
from tueste.models import Tueste
from django.db.models.functions import TruncDate

from .pdf import render_facturacion_pdf
from .services.facturacion import get_available_orders, get_facturacion_report, get_facturacion_report_by_id


@login_required
def facturacion_view(request):
    selected_order = request.GET.get("orden", "")
    report = get_facturacion_report(selected_order)
    return render(
        request,
        "reportes/facturacion.html",
        {
            "orders": get_available_orders(),
            "report": report,
            "selected_order": selected_order,
        },
    )


@login_required
def clientes_view(request):
    return render(request, "reportes/clientes.html")


@login_required
def facturacion_pdf_view(request, orden_id):
    report = get_facturacion_report_by_id(orden_id)
    if report["not_found"] or not report["orden"]:
        raise Http404("Orden de Producción no encontrada")

    pdf_bytes = render_facturacion_pdf(report)
    orden_numero = report["orden"].orden or orden_id
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Facturacion_Orden_{orden_numero}.pdf"'
    return response


class BaseReportView(APIView):
    permission_classes = [IsAuthenticated]

    def _ok(self, data):
        return Response({'data': data})


class OrdenesPorEstadoView(BaseReportView):
    def get(self, request):
        qs = Orden.objects.values('estado_orden__estado_orden').annotate(total=Count('id')).order_by('-total')
        data = [
            {'label': row['estado_orden__estado_orden'] or 'Sin estado', 'value': row['total']}
            for row in qs
        ]
        return self._ok(data)


class InventarioResumenView(BaseReportView):
    def get(self, request):
        qs = InventarioCafe.objects.aggregate(
            total_cantidad=Sum('cantidad'),
            total_sacos=Sum('sacos'),
            total_paquetes=Sum('cantidad_paquetes'),
        )
        data = [
            {'label': 'Kg Café', 'value': qs.get('total_cantidad') or 0},
            {'label': 'Sacos', 'value': qs.get('total_sacos') or 0},
            {'label': 'Paquetes', 'value': qs.get('total_paquetes') or 0},
        ]
        return self._ok(data)


class RendimientoTuesteView(BaseReportView):
    def get(self, request):
        avg_rend = Tueste.objects.aggregate(avg_rend=Avg('rendimiento'))['avg_rend'] or 0
        # Últimos 5 tuestes
        ultimos = Tueste.objects.order_by('-id')[:5]
        series = [
            {
                'id': t.id,
                'rendimiento': t.rendimiento,
                'fecha': t.fecha_ingreso,
            }
            for t in ultimos
        ]
        return self._ok({'promedio': round(avg_rend, 2), 'ultimos': series})


class ProduccionDiariaView(BaseReportView):
    def get(self, request):
        days = int(request.GET.get('days', 7))
        since = timezone.now() - timedelta(days=days)
        # Usar el campo existente `fecha_inicio_orden` y truncar a fecha
        qs = (
            Orden.objects
            .filter(fecha_inicio_orden__gte=since)
            .annotate(day=TruncDate('fecha_inicio_orden'))
            .values('day')
            .annotate(total=Count('id'))
            .order_by('day')
        )
        data = [{'label': str(row['day']), 'value': row['total']} for row in qs]
        return self._ok(data)


class KPIsResumenView(BaseReportView):
    """Devuelve KPIs agregados para las tarjetas del dashboard.

    Nota: Cálculos simples; ajustar según reglas reales de negocio.
    """
    def get(self, request):
        hoy = timezone.now().date()
        ayer = hoy - timedelta(days=1)
        hace_7 = hoy - timedelta(days=7)

        # Órdenes hoy / ayer
        ordenes_hoy = Orden.objects.filter(fecha_inicio_orden__date=hoy).count()
        ordenes_ayer = Orden.objects.filter(fecha_inicio_orden__date=ayer).count()

        # En proceso / completadas (estado global y variante día anterior)
        en_proceso_filter = Q(estado_orden__estado_orden__icontains='proceso')
        completadas_filter = Q(estado_orden__estado_orden__icontains='complet') | Q(estado_orden__estado_orden__icontains='cerr')

        en_proceso_hoy = Orden.objects.filter(fecha_inicio_orden__date=hoy).filter(en_proceso_filter).count()
        en_proceso_ayer = Orden.objects.filter(fecha_inicio_orden__date=ayer).filter(en_proceso_filter).count()

        completadas_hoy = Orden.objects.filter(fecha_inicio_orden__date=hoy).filter(completadas_filter).count()
        completadas_ayer = Orden.objects.filter(fecha_inicio_orden__date=ayer).filter(completadas_filter).count()

        # Activas creadas hoy vs ayer (no completadas/cerradas)
        activas_hoy = (
            Orden.objects.filter(fecha_inicio_orden__date=hoy)
            .exclude(completadas_filter)
            .count()
        )
        activas_ayer = (
            Orden.objects.filter(fecha_inicio_orden__date=ayer)
            .exclude(completadas_filter)
            .count()
        )

        # Pendientes de entrega: órdenes con fecha_entrega >= hoy (o sin fecha) y que NO estén completadas/cerradas
        pendientes_entrega_total = (
            Orden.objects
            .filter(Q(fecha_entrega__date__gte=hoy) | Q(fecha_entrega__isnull=True))
            .exclude(completadas_filter)
            .count()
        )
        pendientes_entrega_hoy = (
            Orden.objects
            .filter(fecha_inicio_orden__date=hoy)
            .filter(Q(fecha_entrega__date__gte=hoy) | Q(fecha_entrega__isnull=True))
            .exclude(completadas_filter)
            .count()
        )
        pendientes_entrega_ayer = (
            Orden.objects
            .filter(fecha_inicio_orden__date=ayer)
            .filter(Q(fecha_entrega__date__gte=ayer) | Q(fecha_entrega__isnull=True))
            .exclude(completadas_filter)
            .count()
        )

        # Inventario actual (no histórico); delta contra promedio simple últimos 7 días si existe campo fecha_ingreso
        inv = InventarioCafe.objects.aggregate(total_kg=Sum('cantidad'))
        total_kg = inv.get('total_kg') or 0
        avg_7 = None
        if hasattr(InventarioCafe, 'fecha_ingreso'):
            avg_qs = (
                InventarioCafe.objects.filter(fecha_ingreso__date__gte=hace_7, fecha_ingreso__date__lt=hoy)
                .aggregate(avg_kg=Avg('cantidad'))
            )
            avg_7 = avg_qs.get('avg_kg') or 0

        # Rendimiento promedio hoy vs promedio 7 días previos (excluyendo hoy)
        rend_prom = Tueste.objects.aggregate(r=Avg('rendimiento')).get('r') or 0
        rend_7_prev = (
            Tueste.objects.filter(fecha_ingreso__date__gte=hace_7, fecha_ingreso__date__lt=hoy)
            .aggregate(r=Avg('rendimiento')).get('r') or 0
        )

        def delta(actual, ref):
            if ref in [None, 0]:
                return None
            return round(((actual - ref) / ref) * 100, 2)

        # Totales globales
        op_activas_total = Orden.objects.exclude(completadas_filter).count()
        en_proceso_total = Orden.objects.filter(en_proceso_filter).count()
        completadas_total = Orden.objects.filter(completadas_filter).count()

        data = {
            'ordenes_hoy': ordenes_hoy,
            'ordenes_hoy_delta': delta(ordenes_hoy, ordenes_ayer),
            'ordenes_hoy_ref': ordenes_ayer,
            'op_activas_total': op_activas_total,
            'op_activas_delta': delta(activas_hoy, activas_ayer),
            'op_activas_ref': activas_ayer,
            # Nuevo KPI: Pendientes de entrega
            'pendientes_entrega_total': pendientes_entrega_total,
            'pendientes_entrega_delta': delta(pendientes_entrega_hoy, pendientes_entrega_ayer),
            'pendientes_entrega_ref': pendientes_entrega_ayer,
            'en_proceso': en_proceso_hoy,
            'en_proceso_delta': delta(en_proceso_hoy, en_proceso_ayer),
            'en_proceso_ref': en_proceso_ayer,
            'completadas': completadas_hoy,
            'completadas_delta': delta(completadas_hoy, completadas_ayer),
            'completadas_ref': completadas_ayer,
            'en_proceso_total': en_proceso_total,
            'completadas_total': completadas_total,
            'inventario_kg': total_kg,
            'inventario_kg_delta': delta(total_kg, avg_7) if avg_7 is not None else None,
            'inventario_kg_ref': avg_7,
            'rend_promedio': round(rend_prom, 2),
            'rend_promedio_delta': delta(rend_prom, rend_7_prev),
            'rend_promedio_ref': rend_7_prev,
        }
        return self._ok(data)
