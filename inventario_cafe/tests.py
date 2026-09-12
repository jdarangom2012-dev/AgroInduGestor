from django.test import TestCase

from inventario_cafe.models import InventarioCafe
from inventario_cafe.views import InventarioCafeForm


class CantidadExistenteTests(TestCase):
    def test_al_crear_copia_la_cantidad_ingresada(self):
        inventario = InventarioCafe.objects.create(cantidad=25, cantidad_existente=999)

        self.assertEqual(inventario.cantidad, 25)
        self.assertEqual(inventario.cantidad_existente, 25)

    def test_al_editar_no_recalcula_la_cantidad_existente(self):
        inventario = InventarioCafe.objects.create(cantidad=25)
        inventario.cantidad = 40
        inventario.save()
        inventario.refresh_from_db()

        self.assertEqual(inventario.cantidad, 40)
        self.assertEqual(inventario.cantidad_existente, 25)

    def test_el_formulario_no_permite_modificar_la_cantidad_existente(self):
        inventario = InventarioCafe.objects.create(cantidad=25)
        form = InventarioCafeForm(
            data={'cantidad': '40', 'cantidad_existente': '999'},
            instance=inventario,
        )

        self.assertTrue(form.is_valid(), form.errors)
        actualizado = form.save()
        self.assertEqual(actualizado.cantidad, 40)
        self.assertEqual(actualizado.cantidad_existente, 25)
