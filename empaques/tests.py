from django.test import TestCase

from cafe_empaque.models import CafeEmpaque
from clientes.models import Cliente
from estado_tareas.models import EstadoTarea
from nivel_molienda.models import NivelMolienda
from ordenes.models import DetalleEmpaqueOrden
from ordenes.models import Orden
from tamano_empaque.models import TamanoEmpaque

from empaques.forms import EmpaqueForm, build_detalle_empaque_formset
from empaques.models import Empaque
from empaques.views import (
    calcular_total_empacado_desde_post,
    obtener_empaque_recibido_rows,
    sincronizar_resumen_empaque,
)


class EmpaqueDetalleFormsetTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre='Cliente', apellidos='Empaque')
        self.orden = Orden.objects.create(orden='OP-EMP-001', cliente=self.cliente)
        self.estado = EstadoTarea.objects.create(estado_tareas='Pendiente')
        self.empaque_cafe = CafeEmpaque.objects.create(empaque_cafe='Bolsa valvula')
        self.tamano = TamanoEmpaque.objects.create(tamano_empaque='500g')
        self.molienda = NivelMolienda.objects.create(nivel_molienda='Media')

    def _detalle_management(self, total_forms, initial_forms=0):
        return {
            'detalle_empaque-TOTAL_FORMS': str(total_forms),
            'detalle_empaque-INITIAL_FORMS': str(initial_forms),
            'detalle_empaque-MIN_NUM_FORMS': '0',
            'detalle_empaque-MAX_NUM_FORMS': '1000',
        }

    def test_nuevo_empaque_requiere_al_menos_una_linea(self):
        form = EmpaqueForm(
            data={
                'orden': self.orden.pk,
                'estado_tareas': self.estado.pk,
                'cant_etiquetas': '10',
                'emp_clientes': '5',
                'notas': 'Prueba',
            }
        )
        formset = build_detalle_empaque_formset(
            data={
                **self._detalle_management(total_forms=1),
                'detalle_empaque-0-empaque_cafe': '',
                'detalle_empaque-0-tamano_empaque': '',
                'detalle_empaque-0-pedido': '',
                'detalle_empaque-0-empacado': '',
                'detalle_empaque-0-nivel_molienda': '',
                'detalle_empaque-0-notas': '',
            },
            instance=form.instance,
        )

        self.assertTrue(form.is_valid())
        self.assertFalse(formset.is_valid())
        self.assertIn('Debe registrar al menos una linea de empaque.', formset.non_form_errors()[0])

    def test_cliente_se_inicializa_desde_la_orden_en_formulario_enlazado(self):
        form = EmpaqueForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado.pk),
                'cant_etiquetas': '3',
                'emp_clientes': '2',
                'notas': 'Con cliente',
            }
        )

        self.assertEqual(form.initial.get('cliente'), self.cliente.pk)
        self.assertEqual(form.fields['cliente'].initial, self.cliente.pk)
        self.assertIn('data-cliente-id="%s"' % self.cliente.pk, str(form['orden']))

    def test_ordenes_disponibles_solo_incluyen_empaque_si_true(self):
        orden_sin_empaque = Orden.objects.create(
            orden='OP-EMP-002',
            cliente=self.cliente,
            empaque_flag=False,
        )
        orden_con_empaque = Orden.objects.create(
            orden='OP-EMP-003',
            cliente=self.cliente,
            empaque_flag=True,
        )

        form = EmpaqueForm()

        self.assertIn(self.orden, form.fields['orden'].queryset)
        self.assertIn(orden_con_empaque, form.fields['orden'].queryset)
        self.assertNotIn(orden_sin_empaque, form.fields['orden'].queryset)

    def test_orden_cliente_select_incluye_trabajo_empaque_data_attr(self):
        orden_no = Orden.objects.create(
            orden='OP-EMP-004',
            cliente=self.cliente,
            trabajo_empaque=False,
        )
        orden_si = Orden.objects.create(
            orden='OP-EMP-005',
            cliente=self.cliente,
            trabajo_empaque=True,
        )
        form = EmpaqueForm()
        rendered = str(form['orden'])

        self.assertIn(f'data-trabajo-empaque="0"', rendered)
        self.assertIn(f'data-trabajo-empaque="1"', rendered)
        self.assertIn(f'value="{orden_no.pk}"', rendered)
        self.assertIn(f'value="{orden_si.pk}"', rendered)

    def test_sincroniza_totales_y_referencias_desde_el_detalle(self):
        empaque = Empaque.objects.create(orden=self.orden, estado_tareas=self.estado, notas='Base')
        formset = build_detalle_empaque_formset(
            data={
                **self._detalle_management(total_forms=1),
                'detalle_empaque-0-id': '',
                'detalle_empaque-0-empaque_cafe': str(self.empaque_cafe.pk),
                'detalle_empaque-0-tamano_empaque': str(self.tamano.pk),
                'detalle_empaque-0-pedido': '25',
                'detalle_empaque-0-empacado': '20',
                'detalle_empaque-0-nivel_molienda': str(self.molienda.pk),
                'detalle_empaque-0-notas': 'Fila 1',
                'detalle_empaque-0-suministro': 'on',
            },
            instance=empaque,
        )

        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        sincronizar_resumen_empaque(empaque)
        empaque.refresh_from_db()

        self.assertEqual(empaque.cant_empaque, 25)
        self.assertEqual(empaque.cant_empacada, 20)
        self.assertEqual(empaque.emp_clientes, 20)
        self.assertEqual(empaque.total_empaques, 25)
        self.assertEqual(empaque.total_paquetes, 20)
        self.assertEqual(empaque.tamano_id, self.tamano.pk)
        self.assertEqual(empaque.nivel_molienda_id, self.molienda.pk)
        self.assertEqual(empaque.detalles.count(), 1)

    def test_calcula_total_empacado_desde_post_ignorando_filas_eliminadas(self):
        total = calcular_total_empacado_desde_post({
            **self._detalle_management(total_forms=3),
            'detalle_empaque-0-empacado': '7',
            'detalle_empaque-1-empacado': '5',
            'detalle_empaque-1-DELETE': 'on',
            'detalle_empaque-2-empacado': '4',
        })

        self.assertEqual(total, 11)

    def test_formulario_guarda_cant_empacada_y_total_paquetes_en_modelo(self):
        form = EmpaqueForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado.pk),
                'cant_etiquetas': '0',
                'emp_clientes': '12',
                'total_paquetes': '9',
                'notas': 'Persistencia',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        empaque = form.save()

        self.assertEqual(empaque.cant_empacada, 12)
        self.assertEqual(empaque.emp_clientes, 12)
        self.assertEqual(empaque.total_paquetes, 9)

    def test_sincronizar_resumen_no_sobrescribe_total_paquetes_manual(self):
        class FakeDetalle:
            def __init__(self, pedido, empacado, tamano_empaque, nivel_molienda):
                self.pedido = pedido
                self.empacado = empacado
                self.tamano_empaque = tamano_empaque
                self.nivel_molienda = nivel_molienda

        class FakeQuerySet:
            def __init__(self, items):
                self.items = items

            def select_related(self, *args, **kwargs):
                return self

            def order_by(self, *args, **kwargs):
                return self.items

        class FakeInstance:
            def __init__(self):
                self.detalles = FakeQuerySet([
                    FakeDetalle(10, 7, self.tamano, self.molienda),
                ])
                self.tamano = None
                self.nivel_molienda = None
                self.cant_empaque = None
                self.cant_empacada = None
                self.emp_clientes = None
                self.total_empaques = None
                self.total_paquetes = 56
                self.saved = False

            def save(self):
                self.saved = True

        instance = FakeInstance()
        instance.detalles.items[0].tamano_empaque = self.tamano
        instance.detalles.items[0].nivel_molienda = self.molienda

        sincronizar_resumen_empaque(instance)

        self.assertEqual(instance.total_paquetes, 56)
        self.assertEqual(instance.emp_clientes, 7)
        self.assertTrue(instance.saved)

    def test_nuevo_empaque_permte_cant_etiquetas_en_cero_si_lleva_etiquetas(self):
        form = EmpaqueForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado.pk),
                'lleva_etiquetas': 'on',
                'cant_etiquetas': '0',
                'emp_clientes': '0',
                'notas': 'Alta',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_edicion_exige_cant_etiquetas_si_lleva_etiquetas(self):
        estado_completada = EstadoTarea.objects.create(estado_tareas='Completada')
        empaque = Empaque.objects.create(
            orden=self.orden,
            estado_tareas=estado_completada,
            lleva_etiquetas=True,
            cant_etiquetas=0,
            emp_clientes=3,
            notas='Base',
        )
        form = EmpaqueForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(estado_completada.pk),
                'lleva_etiquetas': 'on',
                'cant_etiquetas': '0',
                'emp_clientes': '0',
                'notas': 'Edicion',
            },
            instance=empaque,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            EmpaqueForm.CANT_ETIQUETAS_REQUERIDA_ERROR,
            form.errors['cant_etiquetas'],
        )

    def test_edicion_no_valida_cant_etiquetas_si_estado_no_es_completada(self):
        empaque = Empaque.objects.create(
            orden=self.orden,
            estado_tareas=self.estado,
            lleva_etiquetas=True,
            cant_etiquetas=0,
            emp_clientes=3,
            notas='Base',
        )
        form = EmpaqueForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado.pk),
                'lleva_etiquetas': 'on',
                'cant_etiquetas': '0',
                'emp_clientes': '0',
                'notas': 'Edicion',
            },
            instance=empaque,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_edicion_no_valida_cant_etiquetas_si_no_lleva_etiquetas(self):
        empaque = Empaque.objects.create(
            orden=self.orden,
            estado_tareas=self.estado,
            lleva_etiquetas=False,
            cant_etiquetas=0,
            emp_clientes=3,
            notas='Base',
        )
        form = EmpaqueForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado.pk),
                'cant_etiquetas': '0',
                'emp_clientes': '0',
                'notas': 'Edicion',
            },
            instance=empaque,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_emp_clientes_permanece_solo_lectura_en_formulario(self):
        form = EmpaqueForm()

        self.assertEqual(form.fields['emp_clientes'].widget.attrs.get('readonly'), 'readonly')

    def test_nuevo_empaque_permite_guardar_pedido_y_empacado_en_cero(self):
        formset = build_detalle_empaque_formset(
            data={
                **self._detalle_management(total_forms=1),
                'detalle_empaque-0-id': '',
                'detalle_empaque-0-empaque_cafe': str(self.empaque_cafe.pk),
                'detalle_empaque-0-tamano_empaque': str(self.tamano.pk),
                'detalle_empaque-0-pedido': '0',
                'detalle_empaque-0-empacado': '0',
                'detalle_empaque-0-nivel_molienda': str(self.molienda.pk),
                'detalle_empaque-0-notas': 'Alta con cantidades en cero',
            },
            instance=Empaque(),
        )

        self.assertTrue(formset.is_valid(), formset.errors)

    def test_editar_empaque_requiere_pedido_mayor_a_cero(self):
        empaque = Empaque.objects.create(orden=self.orden, estado_tareas=self.estado, notas='Base')
        formset = build_detalle_empaque_formset(
            data={
                **self._detalle_management(total_forms=1),
                'detalle_empaque-0-id': '',
                'detalle_empaque-0-empaque_cafe': str(self.empaque_cafe.pk),
                'detalle_empaque-0-tamano_empaque': str(self.tamano.pk),
                'detalle_empaque-0-pedido': '0',
                'detalle_empaque-0-empacado': '5',
                'detalle_empaque-0-nivel_molienda': str(self.molienda.pk),
                'detalle_empaque-0-notas': 'Edicion invalida',
            },
            instance=empaque,
        )

        self.assertFalse(formset.is_valid())
        self.assertIn('Debe ingresar el pedido.', formset.forms[0].errors['pedido'])

    def test_editar_empaque_requiere_empacado_mayor_a_cero(self):
        empaque = Empaque.objects.create(orden=self.orden, estado_tareas=self.estado, notas='Base')
        formset = build_detalle_empaque_formset(
            data={
                **self._detalle_management(total_forms=1),
                'detalle_empaque-0-id': '',
                'detalle_empaque-0-empaque_cafe': str(self.empaque_cafe.pk),
                'detalle_empaque-0-tamano_empaque': str(self.tamano.pk),
                'detalle_empaque-0-pedido': '5',
                'detalle_empaque-0-empacado': '',
                'detalle_empaque-0-nivel_molienda': str(self.molienda.pk),
                'detalle_empaque-0-notas': 'Edicion invalida',
            },
            instance=empaque,
        )

        self.assertFalse(formset.is_valid())
        self.assertIn('Debe ingresar lo empacado.', formset.forms[0].errors['empacado'])

    def test_obtener_empaque_recibido_rows_usa_detalle_de_la_orden(self):
        DetalleEmpaqueOrden.objects.create(
            orden=self.orden,
            empaque_cafe=self.empaque_cafe,
            tamano_empaque=self.tamano,
            cantidad=200,
        )

        rows = obtener_empaque_recibido_rows(self.orden)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].empaque_cafe_id, self.empaque_cafe.id)
        self.assertEqual(rows[0].tamano_empaque_id, self.tamano.id)
        self.assertEqual(rows[0].cantidad, 200)

    def test_obtener_empaque_recibido_rows_retorna_vacio_sin_orden(self):
        self.assertEqual(obtener_empaque_recibido_rows(None), [])