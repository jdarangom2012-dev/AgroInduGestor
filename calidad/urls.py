from django.urls import path

from . import views


urlpatterns = [
    path('calidad/listar/', views.listar_calidad, name='calidad_listar'),
    path('calidad/nuevo/', views.agregar_calidad, name='calidad_nuevo'),
    path('calidad/<int:pk>/editar/', views.editar_calidad, name='calidad_editar'),
    path('calidad/<int:pk>/pdf/', views.exportar_calidad_pdf, name='calidad_pdf'),
    path('calidad/analisis-sensorial/', views.listar_analisis_sensorial, name='analisis_sensorial_listar'),
    path('calidad/analisis-sensorial/nuevo/', views.agregar_analisis_sensorial, name='analisis_sensorial_nuevo'),
    path('calidad/analisis-sensorial/<int:pk>/editar/', views.editar_analisis_sensorial, name='analisis_sensorial_editar'),
    path('calidad/analisis-sensorial/<int:pk>/pdf/', views.exportar_analisis_sensorial_pdf, name='analisis_sensorial_pdf'),
    path('calidad/analisis-sensorial/<int:pk>/eliminar/', views.eliminar_analisis_sensorial, name='analisis_sensorial_eliminar'),
]
