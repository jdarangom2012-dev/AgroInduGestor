from django.db import transaction
from django.utils import timezone

from .models import InventarioCafe


class SaldoCafeInsuficiente(Exception):
    pass


def vaciar_saldo(inventario_id):
    """Deja el saldo en cero sin borrar el registro ni sus relaciones."""
    InventarioCafe.objects.filter(pk=inventario_id).update(
        cantidad_existente=0,
        updated_at=timezone.now(),
    )


@transaction.atomic
def actualizar_movimientos(inventario):
    """Aplica solo la diferencia frente a los kilos ya registrados."""
    anterior = InventarioCafe.objects.select_for_update().get(pk=inventario.pk)
    diferencia = (
        (inventario.kilos_ingresar or 0) - (anterior.kilos_ingresar or 0)
        - (inventario.kilos_sacar or 0) + (anterior.kilos_sacar or 0)
    )
    nuevo_saldo = (anterior.cantidad_existente or 0) + diferencia
    if nuevo_saldo < -1e-9:
        raise SaldoCafeInsuficiente(
            f'No hay suficientes kilos disponibles. Saldo actual: {(anterior.cantidad_existente or 0):g} kg.'
        )
    inventario.cantidad_existente = round(max(nuevo_saldo, 0), 2)
    inventario.save(update_fields=[
        'cantidad', 'kilos_ingresar', 'kilos_sacar', 'notas',
        'cantidad_existente', 'updated_at',
    ])
