from django.contrib import admin
from .models import InventarioCafe


@admin.register(InventarioCafe)
class InventarioCafeAdmin(admin.ModelAdmin):
    list_display = ('id', 'codigo', 'cliente', 'empaquecafe', 'cantidad', 'cantidad_existente', 'sacos')
    search_fields = ('codigo',)
