from django.db import transaction

from inventario_cafe.models import InventarioCafe


class SaldoInventarioInsuficiente(Exception):
    pass


def _peso(valor):
    return max(float(valor or 0), 0)


@transaction.atomic
def ajustar_inventario_de_orden(orden, orden_anterior):
    """Descuenta una sola vez al pasar una orden existente a Completada."""
    estado_anterior = (getattr(orden_anterior.estado_orden, 'estado_orden', '') or '').strip().casefold()
    estado_nuevo = (getattr(orden.estado_orden, 'estado_orden', '') or '').strip().casefold()
    if estado_anterior == 'completada' or estado_nuevo != 'completada' or orden_anterior.inventario_descontado:
        return

    inventario_nuevo_id = orden.id_inven_cafe_id
    peso_nuevo = _peso(orden.peso)

    debe_descontar = bool(inventario_nuevo_id and peso_nuevo > 0)
    if debe_descontar:
        try:
            nuevo = InventarioCafe.objects.select_for_update().get(pk=inventario_nuevo_id)
        except InventarioCafe.DoesNotExist:
            raise SaldoInventarioInsuficiente("El inventario de café seleccionado ya no existe.")

        disponible = float(nuevo.cantidad_existente or 0)
        if disponible + 1e-9 < peso_nuevo:
            raise SaldoInventarioInsuficiente(
                f"Inventario insuficiente: hay {disponible:g} kg disponibles "
                f"y el Peso Neto es {peso_nuevo:g} kg."
            )
        nuevo.cantidad_existente = round(disponible - peso_nuevo, 2)
        nuevo.save(update_fields=["cantidad_existente"])

    orden.inventario_descontado = debe_descontar
