from django.contrib import admin

from .models import Calidad


@admin.register(Calidad)
class CalidadAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha_ingreso', 'orden', 'cliente', 'proceso', 'muestra_numero')
    search_fields = ('orden', 'muestra_numero', 'cliente__nombre', 'cliente__apellidos')
    list_select_related = ('cliente', 'proceso')
