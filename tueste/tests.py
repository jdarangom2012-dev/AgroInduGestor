from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from clientes.models import Cliente
from inventario_cafe.models import InventarioCafe
from nivel_tueste.models import NivelTueste
from estado_ordenes.models import EstadoOrden
from estado_tareas.models import EstadoTarea
from ordenes.models import Orden

from .models import DetalleTueste, Tueste
from .views import (
    COMPLETADA_BATCHES_PENDIENTES_ERROR,
    KILOS_VERDES_BATCHES_REQUERIDOS_ERROR,
    TuesteForm,
)


class TuesteFormTests(TestCase):
    def setUp(self):
        self.estado_tarea_completada = EstadoTarea.objects.create(estado_tareas='Completada')
        self.estado_orden_completada = EstadoOrden.objects.create(estado_orden='Completada')
        self.estado_orden_pendiente = EstadoOrden.objects.create(estado_orden='Pendiente')

        self.tueste = Tueste.objects.create(
            estado_tareas=self.estado_tarea_completada,
            fecha_ingreso=timezone.now(),
            peso_cafe_vede_total=10,
            peso_cafe_tostado_total=8,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

    def test_completada_bloquea_batches_pendientes(self):
        DetalleTueste.objects.create(
            tueste=self.tueste,
            estado_orden=self.estado_orden_pendiente,
            numero_batch=1,
            kilos_verde=5,
            kilos_tostado=4,
        )

        form = TuesteForm(
            data={
                'estado_tareas': str(self.estado_tarea_completada.pk),
                'peso_cafe_vede_total': '10',
                'peso_cafe_tostado_total': '8',
            },
            instance=self.tueste,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(COMPLETADA_BATCHES_PENDIENTES_ERROR, form.non_field_errors())

    def test_bloquea_guardado_si_algun_batch_tiene_kilos_verdes_en_cero(self):
        DetalleTueste.objects.create(
            tueste=self.tueste,
            estado_orden=self.estado_orden_completada,
            numero_batch=1,
            kilos_verde=0,
            kilos_tostado=4,
        )

        form = TuesteForm(
            data={
                'estado_tareas': str(self.estado_tarea_completada.pk),
                'peso_cafe_vede_total': '10',
                'peso_cafe_tostado_total': '8',
            },
            instance=self.tueste,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(KILOS_VERDES_BATCHES_REQUERIDOS_ERROR, form.non_field_errors())

    def test_bloquea_guardado_si_algun_batch_tiene_kilos_verdes_nulos(self):
        DetalleTueste.objects.create(
            tueste=self.tueste,
            estado_orden=self.estado_orden_completada,
            numero_batch=1,
            kilos_verde=None,
            kilos_tostado=4,
        )

        form = TuesteForm(
            data={
                'estado_tareas': str(self.estado_tarea_completada.pk),
                'peso_cafe_vede_total': '10',
                'peso_cafe_tostado_total': '8',
            },
            instance=self.tueste,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(KILOS_VERDES_BATCHES_REQUERIDOS_ERROR, form.non_field_errors())

    def test_completada_permite_cuando_todos_los_batches_estan_completados(self):
        DetalleTueste.objects.create(
            tueste=self.tueste,
            estado_orden=self.estado_orden_completada,
            numero_batch=1,
            kilos_verde=5,
            kilos_tostado=4,
        )

        form = TuesteForm(
            data={
                'estado_tareas': str(self.estado_tarea_completada.pk),
                'peso_cafe_vede_total': '10',
                'peso_cafe_tostado_total': '8',
            },
            instance=self.tueste,
        )

        self.assertTrue(form.is_valid(), form.errors)


class BatchTuestePersistenceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='secret123',
        )
        self.client.force_login(self.user)

        self.estado_tarea = EstadoTarea.objects.create(estado_tareas='Pendiente')
        self.estado_orden = EstadoOrden.objects.create(estado_orden='Completada')
        self.nivel_tueste = NivelTueste.objects.create(nivel_tueste='Medio')
        self.cliente = Cliente.objects.create(nombre='Cliente', apellidos='Prueba')
        self.inventario = InventarioCafe.objects.create(
            cliente=self.cliente,
            codigo='INV-001',
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self.orden = Orden.objects.create(
            orden='ORD-001',
            cliente=self.cliente,
            id_inven_cafe=self.inventario,
        )
        self.tueste = Tueste.objects.create(
            orden=self.orden,
            inventario_cafe_ref=self.inventario,
            estado_tareas=self.estado_tarea,
            nivel_tueste=self.nivel_tueste,
            fecha_ingreso=timezone.now(),
            peso_cafe_vede_total=99,
            peso_cafe_tostado_total=88,
            rendimiento=112.5,
            notas='Notas encabezado',
            notas_op='Notas OP encabezado',
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

    def assert_tueste_header_intacto(self, tueste):
        self.assertEqual(tueste.orden_id, self.orden.id)
        self.assertEqual(tueste.orden.cliente_id, self.cliente.id)
        self.assertEqual(tueste.inventario_cafe_ref_id, self.inventario.id)
        self.assertEqual(tueste.estado_tareas_id, self.estado_tarea.id)
        self.assertEqual(tueste.nivel_tueste_id, self.nivel_tueste.id)
        self.assertEqual(tueste.notas, 'Notas encabezado')
        self.assertEqual(tueste.notas_op, 'Notas OP encabezado')

    def assert_listado_conserva_campos(self):
        response = self.client.get(f"{reverse('ordenes_tueste_listar')}?fragment=1")
        self.assertContains(response, 'ORD-001')
        self.assertContains(response, 'Cliente Prueba')
        self.assertContains(response, 'INV-001')
        self.assertContains(response, 'Notas encabezado')
        self.assertContains(response, 'Notas OP encabezado')
        self.assertContains(response, 'Pendiente')

    def test_agregar_batch_recalcula_totales_sin_borrar_encabezado(self):
        response = self.client.post(
            reverse('orden_tueste_batch_nuevo', args=[self.tueste.pk]),
            data={
                'estado_orden': str(self.estado_orden.pk),
                'nivel_tueste': str(self.nivel_tueste.pk),
                'kilos_verde': '12.5',
                'kilos_tostado': '10.0',
                'observaciones': 'Primer batch',
            },
        )

        self.assertEqual(response.status_code, 302)
        tueste = Tueste.objects.select_related('orden__cliente', 'inventario_cafe_ref', 'estado_tareas', 'nivel_tueste').get(pk=self.tueste.pk)
        self.assert_tueste_header_intacto(tueste)
        self.assertEqual(tueste.peso_cafe_vede_total, 12.5)
        self.assertEqual(tueste.peso_cafe_tostado_total, 10.0)
        self.assertEqual(tueste.rendimiento, 125.0)
        self.assert_listado_conserva_campos()

    def test_editar_batch_recalcula_totales_sin_borrar_encabezado(self):
        detalle = DetalleTueste.objects.create(
            tueste=self.tueste,
            estado_orden=self.estado_orden,
            nivel_tueste=self.nivel_tueste,
            numero_batch=1,
            kilos_verde=8,
            kilos_tostado=6,
            observaciones='Inicial',
            fecha_ingreso=timezone.now(),
        )
        self.tueste.refresh_from_db()

        response = self.client.post(
            reverse('orden_tueste_batch_editar', args=[self.tueste.pk, detalle.pk]),
            data={
                'estado_orden': str(self.estado_orden.pk),
                'nivel_tueste': str(self.nivel_tueste.pk),
                'kilos_verde': '15.0',
                'kilos_tostado': '12.0',
                'observaciones': 'Actualizado',
            },
        )

        self.assertEqual(response.status_code, 302)
        tueste = Tueste.objects.select_related('orden__cliente', 'inventario_cafe_ref', 'estado_tareas', 'nivel_tueste').get(pk=self.tueste.pk)
        self.assert_tueste_header_intacto(tueste)
        self.assertEqual(tueste.peso_cafe_vede_total, 15.0)
        self.assertEqual(tueste.peso_cafe_tostado_total, 12.0)
        self.assertEqual(tueste.rendimiento, 125.0)
        self.assert_listado_conserva_campos()