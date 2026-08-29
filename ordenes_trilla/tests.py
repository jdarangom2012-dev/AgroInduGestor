from django.test import TestCase

from clientes.models import Cliente
from estado_ordenes.models import EstadoOrden
from estado_tareas.models import EstadoTarea
from ordenes.models import Orden

from ordenes_trilla.views import OrdenTrillaForm


class OrdenTrillaFormValidationTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre='Cliente Test')
        self.orden = Orden.objects.create(orden='OP-TRI-001', cliente=self.cliente)
        self.estado_pendiente = EstadoTarea.objects.create(estado_tareas='Pendiente')
        self.estado_completada = EstadoTarea.objects.create(estado_tareas='Completada')

    def _base_data(self):
        return {
            'cliente': str(self.cliente.pk),
            'orden': str(self.orden.pk),
            'notas': 'Prueba de validación',
        }

    def test_completada_requiere_peso_cafe_neto_y_verde_mayores_a_cero(self):
        form = OrdenTrillaForm(
            data={
                **self._base_data(),
                'estado_tareas': str(self.estado_completada.pk),
                'peso_cafe_bruto': '0',
                'peso_cafe_verde': '0',
                'rendimiento': '0',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            'No es posible completar la Orden de Trilla. Los campos Peso Café Neto y Peso Café Verde deben ser mayores a cero.',
            form.non_field_errors(),
        )

    def test_completada_permite_guardar_con_pesos_positivos(self):
        form = OrdenTrillaForm(
            data={
                **self._base_data(),
                'estado_tareas': str(self.estado_completada.pk),
                'peso_cafe_bruto': '10.5',
                'peso_cafe_verde': '5.25',
                'rendimiento': '0',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_rendimiento_trilla_recalcula_con_formula_correcta(self):
        form = OrdenTrillaForm(
            data={
                **self._base_data(),
                'estado_tareas': str(self.estado_pendiente.pk),
                'peso_cafe_bruto': '82',
                'peso_cafe_verde': '60',
                'rendimiento': '0',
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['rendimiento'], 73.17)

    def test_pendiente_permite_guardar_sin_pesos_positivos(self):
        form = OrdenTrillaForm(
            data={
                **self._base_data(),
                'estado_tareas': str(self.estado_pendiente.pk),
                'peso_cafe_bruto': '0',
                'peso_cafe_verde': '0',
                'rendimiento': '0',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_orden_padre_completada_bloquea_creacion(self):
        self.orden.estado_orden = EstadoOrden.objects.create(estado_orden='Completada')
        self.orden.save(update_fields=['estado_orden'])

        form = OrdenTrillaForm(
            data={
                **self._base_data(),
                'estado_tareas': str(self.estado_pendiente.pk),
                'peso_cafe_bruto': '10',
                'peso_cafe_verde': '5',
                'rendimiento': '0',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            'No es posible crear o editar esta tarea porque la Orden de Producción vinculada ya se encuentra en estado Completada.',
            form.errors['orden'],
        )
