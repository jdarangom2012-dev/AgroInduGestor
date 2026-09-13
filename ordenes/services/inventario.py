from django.db import transaction

from inventario_cafe.models import InventarioCafe


class SaldoInventarioInsuficiente(Exception):
    pass


def _peso(valor):
    return max(float(valor or 0), 0)


@transaction.atomic
def ajustar_inventario_de_orden(
    orden,
    *,
    inventario_anterior_id=None,
    peso_bruto_anterior=0,
    descuento_anterior=False,
):
    """Resta el peso bruto una sola vez y ajusta únicamente la diferencia al editar."""
    inventario_nuevo_id = orden.id_inven_cafe_id
    peso_nuevo = _peso(orden.peso_bruto)
    peso_anterior = _peso(peso_bruto_anterior) if descuento_anterior else 0

    ids = sorted({pk for pk in (inventario_anterior_id, inventario_nuevo_id) if pk})
    inventarios = {
        inventario.pk: inventario
        for inventario in InventarioCafe.objects.select_for_update().filter(pk__in=ids)
    }

    if descuento_anterior and inventario_anterior_id in inventarios:
        anterior = inventarios[inventario_anterior_id]
        anterior.cantidad_existente = float(anterior.cantidad_existente or 0) + peso_anterior

    debe_descontar = bool(inventario_nuevo_id and peso_nuevo > 0)
    if debe_descontar:
        nuevo = inventarios.get(inventario_nuevo_id)
        if nuevo is None:
            raise SaldoInventarioInsuficiente("El inventario de café seleccionado ya no existe.")

        disponible = float(nuevo.cantidad_existente or 0)
        if disponible + 1e-9 < peso_nuevo:
            raise SaldoInventarioInsuficiente(
                f"Inventario insuficiente: hay {disponible:g} kg disponibles "
                f"y el Peso Bruto es {peso_nuevo:g} kg."
            )
        nuevo.cantidad_existente = disponible - peso_nuevo

    for inventario in inventarios.values():
        inventario.save(update_fields=["cantidad_existente"])

    orden.inventario_descontado = debe_descontar
