from django.test import TestCase
from django.utils import timezone

from inventario_cafe.models import InventarioCafe
from ordenes.models import Orden
from ordenes.services.inventario import (
    SaldoInventarioInsuficiente,
    ajustar_inventario_de_orden,
)


class AjusteInventarioOrdenTests(TestCase):
    def _inventario(self, cantidad):
        return InventarioCafe.objects.create(
            cantidad=cantidad,
            cantidad_existente=cantidad,
            created_at=timezone.now(),
        )

    def test_crear_orden_descuenta_peso_bruto(self):
        inventario = self._inventario(100)
        orden = Orden(id_inven_cafe=inventario, peso_bruto=30)

        ajustar_inventario_de_orden(orden)

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 70)
        self.assertTrue(orden.inventario_descontado)

    def test_editar_orden_ajusta_solo_la_diferencia(self):
        inventario = self._inventario(70)
        orden = Orden(id_inven_cafe=inventario, peso_bruto=40)

        ajustar_inventario_de_orden(
            orden,
            inventario_anterior_id=inventario.pk,
            peso_bruto_anterior=30,
            descuento_anterior=True,
        )

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 60)

    def test_cambiar_inventario_devuelve_el_anterior_y_descuenta_el_nuevo(self):
        anterior = self._inventario(70)
        nuevo = self._inventario(50)
        orden = Orden(id_inven_cafe=nuevo, peso_bruto=20)

        ajustar_inventario_de_orden(
            orden,
            inventario_anterior_id=anterior.pk,
            peso_bruto_anterior=30,
            descuento_anterior=True,
        )

        anterior.refresh_from_db()
        nuevo.refresh_from_db()
        self.assertEqual(anterior.cantidad_existente, 100)
        self.assertEqual(nuevo.cantidad_existente, 30)

    def test_saldo_insuficiente_no_modifica_inventario(self):
        inventario = self._inventario(10)
        orden = Orden(id_inven_cafe=inventario, peso_bruto=20)

        with self.assertRaises(SaldoInventarioInsuficiente):
            ajustar_inventario_de_orden(orden)

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 10)
