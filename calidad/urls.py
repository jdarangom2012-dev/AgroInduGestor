from django.urls import path

from . import views


urlpatterns = [
    path('calidad/listar/', views.listar_calidad, name='calidad_listar'),
    path('calidad/nuevo/', views.agregar_calidad, name='calidad_nuevo'),
    path('calidad/<int:pk>/editar/', views.editar_calidad, name='calidad_editar'),
    path('calidad/<int:pk>/pdf/', views.exportar_calidad_pdf, name='calidad_pdf'),
]
