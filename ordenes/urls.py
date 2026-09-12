from rest_framework.routers import DefaultRouter
from .viewsets import OrdenViewSet
from django.urls import path
from ordenes import views

router = DefaultRouter()
router.register(r'ordenes', OrdenViewSet)

# Rutas HTML (popups) primero para no ser capturadas por el router
urlpatterns = [
	path('ordenes-produccion/listar/', views.listar_ordenes, name='ordenes_produccion_listar'),
	path('ordenes-produccion/inventarios-por-cliente/', views.inventarios_por_cliente, name='ordenes_inventarios_por_cliente'),
	path('ordenes-produccion/nuevo/', views.add_orden, name='ordenes_produccion_nuevo'),
	path('ordenes-produccion/<int:pk>/ver/', views.view_orden, name='ordenes_produccion_ver'),
	path('ordenes-produccion/<int:pk>/editar/', views.edit_orden, name='ordenes_produccion_editar'),
	path('ordenes-produccion/<int:pk>/eliminar/', views.delete_orden, name='ordenes_produccion_eliminar'),
]

# Rutas API
urlpatterns += router.urls
