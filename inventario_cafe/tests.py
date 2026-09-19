from django.test import TestCase

from inventario_cafe.models import InventarioCafe
from inventario_cafe.views import InventarioCafeForm
from inventario_cafe.services import SaldoCafeInsuficiente, actualizar_movimientos, vaciar_saldo


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

    def test_al_editar_aplica_kilos_entrantes_y_salientes(self):
        inventario = InventarioCafe.objects.create(cantidad=25)
        form = InventarioCafeForm(
            data={
                'cantidad': '25',
                'kilos_ingresar': '5',
                'kilos_sacar': '2',
                'notas': 'Movimiento pendiente de confirmar',
            },
            instance=inventario,
        )

        self.assertTrue(form.is_valid(), form.errors)
        actualizar_movimientos(form.save(commit=False))
        inventario.refresh_from_db()
        self.assertEqual(inventario.kilos_ingresar, 5)
        self.assertEqual(inventario.kilos_sacar, 2)
        self.assertEqual(inventario.notas, 'Movimiento pendiente de confirmar')
        self.assertEqual(inventario.cantidad_existente, 28)

    def test_al_crear_aplica_movimientos_al_saldo_inicial(self):
        inventario = InventarioCafe.objects.create(
            cantidad=25, kilos_ingresar=5, kilos_sacar=2,
        )

        self.assertEqual(inventario.cantidad_existente, 28)

    def test_cantidad_existente_se_guarda_y_muestra_con_dos_decimales(self):
        inventario = InventarioCafe.objects.create(
            cantidad=250, kilos_ingresar=20.09, kilos_sacar=260,
        )

        self.assertEqual(inventario.cantidad_existente, 10.09)
        self.assertEqual(InventarioCafeForm(instance=inventario)['cantidad_existente'].value(), '10.09')

    def test_edicion_sin_cambios_no_repite_movimiento(self):
        inventario = InventarioCafe.objects.create(cantidad=25)
        inventario.kilos_ingresar = 5
        inventario.kilos_sacar = 2
        actualizar_movimientos(inventario)
        actualizar_movimientos(inventario)
        inventario.refresh_from_db()

        self.assertEqual(inventario.cantidad_existente, 28)

    def test_corregir_movimiento_aplica_solo_diferencia(self):
        inventario = InventarioCafe.objects.create(cantidad=25, kilos_ingresar=5, kilos_sacar=2)
        inventario.kilos_ingresar = 8
        inventario.kilos_sacar = 3
        actualizar_movimientos(inventario)
        inventario.refresh_from_db()

        self.assertEqual(inventario.cantidad_existente, 30)

    def test_no_permite_saldo_negativo(self):
        inventario = InventarioCafe.objects.create(cantidad=5)
        inventario.kilos_sacar = 6

        with self.assertRaises(SaldoCafeInsuficiente):
            actualizar_movimientos(inventario)

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 5)

    def test_no_acepta_kilos_negativos(self):
        form = InventarioCafeForm(data={'kilos_ingresar': '-1', 'kilos_sacar': '-2'})

        self.assertFalse(form.is_valid())
        self.assertIn('kilos_ingresar', form.errors)
        self.assertIn('kilos_sacar', form.errors)

    def test_al_editar_solo_permite_los_cuatro_campos_solicitados(self):
        inventario = InventarioCafe.objects.create(
            cantidad=25,
            descripcion='Original',
            sacos=3,
        )
        form = InventarioCafeForm(
            data={
                'cantidad': '40',
                'kilos_ingresar': '5',
                'kilos_sacar': '2',
                'notas': 'Ajuste',
                'descripcion': 'Alterada',
                'sacos': '99',
                'cantidad_existente': '999',
            },
            instance=inventario,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            {name for name, field in form.fields.items() if not field.disabled},
            {'cantidad', 'kilos_ingresar', 'kilos_sacar', 'notas'},
        )
        actualizar_movimientos(form.save(commit=False))
        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad, 40)
        self.assertEqual(inventario.descripcion, 'Original')
        self.assertEqual(inventario.sacos, 3)
        self.assertEqual(inventario.cantidad_existente, 28)

    def test_al_crear_mantiene_los_demas_campos_editables(self):
        form = InventarioCafeForm()

        self.assertFalse(form.fields['descripcion'].disabled)
        self.assertFalse(form.fields['sacos'].disabled)

    def test_vaciar_saldo_conserva_inventario_y_orden_vinculada(self):
        from ordenes.models import Orden

        inventario = InventarioCafe.objects.create(cantidad=25, descripcion='Lote')
        orden = Orden.objects.create(id_inven_cafe=inventario)

        vaciar_saldo(inventario.pk)

        inventario.refresh_from_db()
        self.assertEqual(inventario.cantidad_existente, 0)
        self.assertEqual(inventario.cantidad, 25)
        self.assertEqual(inventario.descripcion, 'Lote')
        self.assertTrue(Orden.objects.filter(pk=orden.pk, id_inven_cafe=inventario).exists())
