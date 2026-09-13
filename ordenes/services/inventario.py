from django.db import transaction

from inventario_cafe.models import InventarioCafe


class SaldoInventarioInsuficiente(Exception):
    pass


def _peso(valor):
    return max(float(valor or 0), 0)


@transaction.atomic
def ajustar_inventario_de_orden(orden):
    """Resta del inventario el peso bruto informado en el guardado actual."""
    inventario_nuevo_id = orden.id_inven_cafe_id
    peso_nuevo = _peso(orden.peso_bruto)

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
                f"y el Peso Bruto es {peso_nuevo:g} kg."
            )
        nuevo.cantidad_existente = disponible - peso_nuevo
        nuevo.save(update_fields=["cantidad_existente"])

    orden.inventario_descontado = debe_descontar
