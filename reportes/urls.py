from django.urls import path
from . import views

urlpatterns = [
    path('reportes/facturacion/', views.facturacion_view, name='reportes_facturacion'),
    path('reportes/clientes/', views.clientes_view, name='reportes_clientes'),
    path('reportes/facturacion/<int:orden_id>/pdf/', views.facturacion_pdf_view, name='reportes_facturacion_pdf'),
    path('reportes/ordenes-por-estado/', views.OrdenesPorEstadoView.as_view()),
    path('reportes/inventario-resumen/', views.InventarioResumenView.as_view()),
    path('reportes/rendimiento-tueste/', views.RendimientoTuesteView.as_view()),
    path('reportes/produccion-diaria/', views.ProduccionDiariaView.as_view()),
    path('reportes/kpis-resumen/', views.KPIsResumenView.as_view()),
]
