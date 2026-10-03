from django.contrib import admin

from .models import AnalisisSensorial, Calidad


@admin.register(Calidad)
class CalidadAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha_ingreso', 'orden', 'cliente', 'proceso', 'muestra_numero')
    search_fields = ('orden', 'muestra_numero', 'cliente__nombre', 'cliente__apellidos')
    list_select_related = ('cliente', 'proceso')


@admin.register(AnalisisSensorial)
class AnalisisSensorialAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'nombre', 'muestra_numero', 'puntaje_total')
    search_fields = ('nombre', 'muestra_numero', 'objetivo')
