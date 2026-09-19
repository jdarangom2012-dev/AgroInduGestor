from django.test import TestCase
from django.utils import timezone

from inventario_cafe.models import InventarioCafe
from estado_ordenes.models import EstadoOrden
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

    def test_orden_sin_completar_no_descuenta(self):
        inventario = self._inventario(100)
        pendiente = EstadoOrden.objects.create(estado_orden='Pendiente')
        orden_anterior = Orden(estado_orden=pendiente)
        orden = Orden(id_inven_cafe=inventario, peso=30, estado_orden=pendiente)

        ajustar_inventario_de_orden(orden, orden_anterior)

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 100)
        self.assertFalse(orden.inventario_descontado)

    def test_al_pasar_a_completada_descuenta_peso_neto_una_vez(self):
        inventario = self._inventario(70)
        pendiente = EstadoOrden.objects.create(estado_orden='Pendiente')
        completada = EstadoOrden.objects.create(estado_orden='Completada')
        anterior = Orden(id_inven_cafe=inventario, peso=40, estado_orden=pendiente)
        orden = Orden(id_inven_cafe=inventario, peso=40, estado_orden=completada)

        ajustar_inventario_de_orden(orden, anterior)

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 30)
        self.assertTrue(orden.inventario_descontado)

        ajustar_inventario_de_orden(orden, orden)
        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 30)

    def test_orden_ya_descontada_no_vuelve_a_descontar(self):
        inventario = self._inventario(70)
        pendiente = EstadoOrden.objects.create(estado_orden='Pendiente')
        completada = EstadoOrden.objects.create(estado_orden='Completada')
        anterior = Orden(estado_orden=pendiente, inventario_descontado=True)
        orden = Orden(id_inven_cafe=inventario, peso=40, estado_orden=completada)

        ajustar_inventario_de_orden(orden, anterior)

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 70)

    def test_saldo_insuficiente_no_modifica_inventario(self):
        inventario = self._inventario(10)
        pendiente = EstadoOrden.objects.create(estado_orden='Pendiente')
        completada = EstadoOrden.objects.create(estado_orden='Completada')
        anterior = Orden(estado_orden=pendiente)
        orden = Orden(id_inven_cafe=inventario, peso=20, estado_orden=completada)

        with self.assertRaises(SaldoInventarioInsuficiente):
            ajustar_inventario_de_orden(orden, anterior)

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 10)
