from django.contrib.auth.models import AnonymousUser
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.utils import timezone

from clientes.models import Cliente
from estado_tareas.models import EstadoTarea
from ordenes.models import Orden

from seleccion_tueste.models import SeleccionTueste
from seleccion_tueste.views import SeleccionTuesteForm


class SeleccionTuesteFormTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre='Cliente', apellidos='Seleccion Tueste')
        self.estado_pendiente = EstadoTarea.objects.create(estado_tareas='Pendiente')
        self.estado_completada = EstadoTarea.objects.create(estado_tareas='Completada')
        self.orden = Orden.objects.create(
            orden='OP-ST-001',
            cliente=self.cliente,
            selec_cafe_tostado=True,
        )

    def test_pendiente_permite_cat_quaker_sin_peso(self):
        form = SeleccionTuesteForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_pendiente.pk),
                'cat_quaker': 'on',
                'notas': 'Parcial',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_completada_exige_pesos(self):
        form = SeleccionTuesteForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_completada.pk),
                'cat_quaker': 'on',
                'notas': 'Completa',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('peso_quaker', form.errors)
        self.assertIn(
            'Debe ingresar un Peso Quaker mayor a cero para completar la tarea.',
            form.errors['peso_quaker'],
        )

    def test_completada_permite_sin_pesos_si_no_hay_categorias_marcadas(self):
        form = SeleccionTuesteForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_completada.pk),
                'notas': 'Completa sin categorias marcadas',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_pendiente_permite_pesos_en_cero(self):
        form = SeleccionTuesteForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_pendiente.pk),
                'cat_quaker': 'on',
                'peso_quaker': '0',
                'cat_grupo1': 'on',
                'desc_grupo1': 'Grupo 1',
                'peso_grupo1': '0',
                'notas': 'Pendiente con pesos en cero',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_completada_exige_descripcion_y_peso_grupo1(self):
        form = SeleccionTuesteForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_completada.pk),
                'cat_grupo1': 'on',
                'peso_grupo1': '0',
                'notas': 'Completa con grupo 1 invalido',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('desc_grupo1', form.errors)
        self.assertIn(
            'Debe ingresar la descripción y un Peso del Grupo 1 mayor a cero.',
            form.errors['desc_grupo1'],
        )

    def test_completada_exige_descripcion_y_peso_grupo2(self):
        form = SeleccionTuesteForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_completada.pk),
                'cat_grupo2': 'on',
                'peso_grupo2': '0',
                'notas': 'Completa con grupo 2 invalido',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('desc_grupo2', form.errors)
        self.assertIn(
            'Debe ingresar la descripción y un Peso del Grupo 2 mayor a cero.',
            form.errors['desc_grupo2'],
        )

    def test_completada_exige_descripcion_y_peso_grupo3(self):
        form = SeleccionTuesteForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_completada.pk),
                'cat_grupo3': 'on',
                'peso_grupo3': '0',
                'notas': 'Completa con grupo 3 invalido',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('desc_grupo3', form.errors)
        self.assertIn(
            'Debe ingresar la descripción y un Peso del Grupo 3 mayor a cero.',
            form.errors['desc_grupo3'],
        )

    def test_listado_muestra_numero_de_orden_no_pk_interna(self):
        orden = Orden.objects.create(
            id=106,
            orden='2319',
            cliente=self.cliente,
            selec_cafe_tostado=True,
        )
        seleccion = SeleccionTueste.objects.create(
            id=2002,
            orden=orden,
            estado_tareas=self.estado_pendiente,
            fecha_ingreso=timezone.now(),
            created_at=timezone.now(),
        )
        page_obj = Paginator([seleccion], 7).page(1)
        request = RequestFactory().get('/ordenes-seleccion-tueste/listar/')
        request.user = AnonymousUser()

        html = render_to_string(
            'seleccion_tueste/_modal_listar_OrdenesSeleccionTueste.html',
            {
                'selecciones': page_obj,
                'page_obj': page_obj,
                'paginator': page_obj.paginator,
                'is_paginated': False,
                'search': '',
                'request': request,
            },
        )

        self.assertIn('<td class="td">2319</td>', html)
        self.assertNotIn('<td class="td">106</td>', html)
