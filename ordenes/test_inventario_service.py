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

    def test_crear_orden_descuenta_peso_neto(self):
        inventario = self._inventario(100)
        orden = Orden(id_inven_cafe=inventario, peso=30)

        ajustar_inventario_de_orden(orden)

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 70)
        self.assertTrue(orden.inventario_descontado)

    def test_editar_orden_descuenta_el_peso_neto_del_guardado(self):
        inventario = self._inventario(70)
        orden = Orden(id_inven_cafe=inventario, peso=40)

        ajustar_inventario_de_orden(orden)

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 30)

    def test_saldo_insuficiente_no_modifica_inventario(self):
        inventario = self._inventario(10)
        orden = Orden(id_inven_cafe=inventario, peso=20)

        with self.assertRaises(SaldoInventarioInsuficiente):
            ajustar_inventario_de_orden(orden)

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 10)
