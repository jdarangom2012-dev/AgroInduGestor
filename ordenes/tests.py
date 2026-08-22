from django.conf import settings
import pytest
@pytest.mark.django_db(transaction=True)
def test_bulk_crud_sqlserver():
    """
    Prueba CRUD completa contra SQL Server: crea, edita y elimina 3 órdenes.
    Verifica que no haya errores y que los cambios se reflejen.
    """
    from clientes.models import Cliente
    from estado_ordenes.models import EstadoOrden
    from empleados.models import Empleado
    from ordenes.models import Orden
    from django.utils import timezone

    # Asegura datos referenciales
    cliente, _ = Cliente.objects.get_or_create(nombre='Cliente Test', defaults={'apellidos': 'Test', 'created_at': timezone.now()})
    estado, _ = EstadoOrden.objects.get_or_create(estado_orden='En Espera')
    empleado = Empleado.objects.first()
    if not empleado:
        empleado = Empleado.objects.create(
            identificacion='9999', nombres='Empleado', apellidos='Test', estado='Activo', fecha_ingreso=timezone.now()
        )

    # Crear 3 órdenes
    ids = []
    for i in range(3):
        o = Orden.objects.create(
            cliente=cliente,
            estado_orden=estado,
            id_empleado=empleado,
            orden=f'ORDSQL{i+1}',
            fecha_ingreso=timezone.now(),
            fecha_inicio_orden=timezone.now(),
            prioridad=1,
        )
        ids.append(o.id)
    assert Orden.objects.filter(id__in=ids).count() == 3

    # Editar cada una
    for oid in ids:
        o = Orden.objects.get(id=oid)
        o.orden = f'EDITSQL{oid}'
        o.prioridad = 2
        o.save()
        o.refresh_from_db()
        assert o.orden.startswith('EDITSQL')
        assert o.prioridad == 2

    # Eliminar todas
    for oid in ids:
        Orden.objects.filter(id=oid).delete()
    assert Orden.objects.filter(id__in=ids).count() == 0
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from .models import DetalleEmpaqueOrden, Orden
from clientes.models import Cliente

class OrdenTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre="Cliente Test")
        from estado_ordenes.models import EstadoOrden
        self.estado_orden = EstadoOrden.objects.create(estado_orden="Pendiente")
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        from django.contrib.auth.models import Permission
        perms = Permission.objects.filter(codename__in=['add_orden', 'change_orden', 'view_orden', 'delete_orden'])
        self.user.user_permissions.set(perms)

    def _detalle_management_data(self, total_forms, initial_forms=0):
        return {
            'detalle_empaque-TOTAL_FORMS': str(total_forms),
            'detalle_empaque-INITIAL_FORMS': str(initial_forms),
            'detalle_empaque-MIN_NUM_FORMS': '0',
            'detalle_empaque-MAX_NUM_FORMS': '1000',
        }

    def _base_orden_data(self, **overrides):
        data = {
            'cliente': self.cliente.id,
            'orden': 'ORD-BASE',
            'estado_orden': self.estado_orden.id,
            'fecha_inicio_orden': '2026-05-19',
            'prioridad': 1,
        }
        data.update(self._detalle_management_data(total_forms=1))
        data.update(overrides)
        return data

    def test_creacion_orden_con_campo_orden(self):
        url = reverse('ordenes_produccion_nuevo')
        data = {
            'cliente': self.cliente.id,
            'orden': 'ORD00001',
                'estado_orden': self.estado_orden.id,
                'estado_inven_cafe': '',
            'fecha_orden': '',
            'fecha_entrega': '',
            'notas': 'Prueba',
            'trilla': False,
            'selec_cafe_verde': False,
            'tueste_flag': False,
            'selec_cafe_tostado': False,
            'molienda_flag': False,
            'empaque_flag': False,
            'conf_trilla': False,
            'conf_sel_verde': False,
            'conf_tueste': False,
            'conf_sel_tostado': False,
            'conf_molienda': False,
            'conf_empaque': False,
            'prioridad': 1,
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        orden = Orden.objects.latest('id')
        self.assertEqual(orden.orden, 'ORD00001')

    def test_no_permite_orden_duplicada_muestra_mensaje(self):
        from django.utils import timezone

        existente = Orden.objects.create(
            cliente=self.cliente,
            orden='ORDSQL99',
            estado_orden=self.estado_orden,
            created_at=timezone.now(),
        )

        url = reverse('ordenes_produccion_nuevo') + '?fragment=1'
        data = {
            'cliente': self.cliente.id,
            'orden': 'ordsqL99',
            'estado_orden': self.estado_orden.id,
            'prioridad': 1,
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La orden de producción ya existe')
        self.assertEqual(Orden.objects.count(), 1)

        existente.refresh_from_db()
        self.assertEqual(existente.orden, 'ORDSQL99')

    def test_edicion_orden_modifica_campo_orden(self):
        from django.utils import timezone
        orden = Orden.objects.create(cliente=self.cliente, orden='ORD00002', estado_orden=self.estado_orden, created_at=timezone.now())
        url = reverse('ordenes_produccion_editar', args=[orden.id])
        data = {
            'cliente': self.cliente.id,
            'orden': 'ORD00099',
                'estado_orden': self.estado_orden.id,
                'estado_inven_cafe': '',
            'fecha_orden': '',
            'fecha_entrega': '',
            'notas': 'Editada',
            'trilla': False,
            'selec_cafe_verde': False,
            'tueste_flag': False,
            'selec_cafe_tostado': False,
            'molienda_flag': False,
            'empaque_flag': False,
            'conf_trilla': False,
            'conf_sel_verde': False,
            'conf_tueste': False,
            'conf_sel_tostado': False,
            'conf_molienda': False,
            'conf_empaque': False,
            'prioridad': 1,
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        orden.refresh_from_db()
        self.assertEqual(orden.orden, 'ORD00099')

    def test_listado_muestra_campo_orden(self):
        from django.utils import timezone
        orden = Orden.objects.create(cliente=self.cliente, orden='ORDLISTA', estado_orden=self.estado_orden, created_at=timezone.now())
        url = reverse('ordenes_produccion_listar')
        response = self.client.get(url)
        self.assertContains(response, 'ORDLISTA')

    def test_bulk_crear_editar_eliminar_tres_ordenes(self):
        # Crear 3 órdenes
        codigos = ['ORDT01', 'ORDT02', 'ORDT03']
        for codigo in codigos:
            url = reverse('ordenes_produccion_nuevo') + '?fragment=1'
            data = {
                'cliente': self.cliente.id,
                'orden': codigo,
                'estado_orden': self.estado_orden.id,
                'prioridad': 1,
            }
            response = self.client.post(url, data, follow=True)
            self.assertEqual(response.status_code, 200)
            # Si hubiera errores de formulario, la plantilla incluiría este texto
            self.assertNotContains(response, 'Hay errores en el formulario')

        self.assertEqual(Orden.objects.count(), 3)

        # Editar cada una con un nuevo código
        for idx, orden in enumerate(Orden.objects.order_by('id')):
            nuevo_codigo = f"{codigos[idx]}E"
            url = reverse('ordenes_produccion_editar', args=[orden.id])
            data = {
                'cliente': self.cliente.id,
                'orden': nuevo_codigo,
                'estado_orden': self.estado_orden.id,
                'prioridad': 2,
            }
            # Usamos el header X-Fragment para evitar redirect y poder inspeccionar contenido
            response = self.client.post(url, data, follow=True, HTTP_X_FRAGMENT='1')
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'Hay errores en el formulario')
            orden.refresh_from_db()
            self.assertEqual(orden.orden, nuevo_codigo)

        # Eliminar las 3 órdenes
        ids = list(Orden.objects.values_list('id', flat=True))
        for oid in ids:
            url = reverse('ordenes_produccion_eliminar', args=[oid])
            response = self.client.post(url, follow=True)
            self.assertEqual(response.status_code, 200)

        self.assertEqual(Orden.objects.count(), 0)

    def test_form_requiere_campos_empaque_cuando_empaque_activo(self):
        from ordenes.forms import OrdenForm

        form = OrdenForm(data={
            'cliente': self.cliente.id,
            'orden': 'ORDPACK01',
            'estado_orden': self.estado_orden.id,
            'fecha_inicio_orden': '2026-05-17',
            'empaque_flag': 'on',
            'prioridad': 1,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('empaque_cafe', form.errors)
        self.assertIn('tamano_empaque', form.errors)

    def test_form_acepta_campos_empaque_cuando_estan_completos(self):
        from ordenes.forms import OrdenForm
        from cafe_empaque.models import CafeEmpaque
        from tamano_empaque.models import TamanoEmpaque

        empaque = CafeEmpaque.objects.create(empaque_cafe='Bolsa Test')
        tamano = TamanoEmpaque.objects.create(tamano_empaque='500g')

        form = OrdenForm(data={
            'cliente': self.cliente.id,
            'orden': 'ORDPACK02',
            'estado_orden': self.estado_orden.id,
            'fecha_inicio_orden': '2026-05-17',
            'conf_empaque': 'on',
            'empaque_cafe': empaque.id,
            'tamano_empaque': tamano.id,
            'prioridad': 1,
        })

        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_form_rechaza_completada_si_hay_confirmaciones_pendientes(self):
        from ordenes.forms import OrdenForm

        estado_completada = EstadoOrden.objects.create(estado_orden='Completada')

        form = OrdenForm(data={
            'cliente': self.cliente.id,
            'orden': 'ORDCOMP01',
            'estado_orden': estado_completada.id,
            'fecha_inicio_orden': '2026-05-17',
            'trilla': 'on',
            'conf_trilla': '',
            'peso_bruto': '10',
            'peso': '10',
            'prioridad': 1,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('No es posible completar la Orden de Producción', str(form.non_field_errors()))

    def test_form_bloquea_completada_si_confirmaciones_ok_pero_faltan_ordenes_hijas(self):
        from ordenes.forms import OrdenForm
        from django.utils import timezone

        estado_completada = EstadoOrden.objects.create(estado_orden='Completada')
        orden = Orden.objects.create(
            cliente=self.cliente,
            orden='ORDCOMP02',
            estado_orden=self.estado_orden,
            fecha_inicio_orden=timezone.now(),
            peso_bruto=10,
            peso=10,
            created_at=timezone.now(),
        )

        form = OrdenForm(data={
            'cliente': self.cliente.id,
            'orden': 'ORDCOMP02',
            'estado_orden': estado_completada.id,
            'fecha_inicio_orden': '2026-05-17',
            'trilla': 'on',
            'conf_trilla': 'on',
            'selec_cafe_verde': 'on',
            'conf_sel_verde': 'on',
            'tueste_flag': 'on',
            'conf_tueste': 'on',
            'selec_cafe_tostado': 'on',
            'conf_sel_tostado': 'on',
            'empaque_flag': 'on',
            'conf_empaque': 'on',
            'peso_bruto': '10',
            'peso': '10',
            'prioridad': 1,
        }, instance=orden)

        self.assertFalse(form.is_valid())
        self.assertIn('procesos requeridos sin una orden registrada', str(form.non_field_errors()))

    def _completion_data(self, orden, estado_completada, **overrides):
        data = {
            'cliente': self.cliente.id,
            'orden': orden.orden,
            'estado_orden': estado_completada.id,
            'fecha_inicio_orden': '2026-05-17',
            'peso_bruto': '10',
            'peso': '10',
            'prioridad': 1,
        }
        data.update(self._detalle_management_data(total_forms=1))
        data.update(overrides)
        return data

    def _create_child_process(self, model, orden, estado_tarea, **extra_fields):
        from django.utils import timezone

        defaults = {
            'orden': orden,
            'estado_tareas': estado_tarea,
            'created_at': timezone.now(),
        }
        defaults.update(extra_fields)
        return model.objects.create(**defaults)

    def test_form_permite_completada_si_procesos_requeridos_estan_completados(self):
        from django.utils import timezone
        from estado_ordenes.models import EstadoOrden
        from estado_tareas.models import EstadoTarea
        from ordenes.forms import OrdenForm
        from ordenes_trilla.models import OrdenTrilla
        from tueste.models import Tueste
        from seleccion_tueste.models import SeleccionTueste
        from ordenes_seleccion_verde.models import OrdenSeleccionVerde
        from empaques.models import Empaque

        estado_completada_orden = EstadoOrden.objects.create(estado_orden='Completada')
        estado_completada_tarea = EstadoTarea.objects.create(estado_tareas='Completada')
        orden = Orden.objects.create(
            cliente=self.cliente,
            orden='ORDPROCOK',
            estado_orden=self.estado_orden,
            fecha_inicio_orden=timezone.now(),
            peso_bruto=10,
            peso=10,
            created_at=timezone.now(),
        )

        for model in (OrdenTrilla, Tueste, SeleccionTueste, OrdenSeleccionVerde, Empaque):
            self._create_child_process(model, orden, estado_completada_tarea)

        form = OrdenForm(
            data=self._completion_data(
                orden,
                estado_completada_orden,
                trilla='on',
                conf_trilla='on',
                selec_cafe_verde='on',
                conf_sel_verde='on',
                tueste_flag='on',
                conf_tueste='on',
                selec_cafe_tostado='on',
                conf_sel_tostado='on',
                empaque_flag='on',
                conf_empaque='on',
            ),
            instance=orden,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_form_bloquea_completada_si_trilla_esta_pendiente(self):
        from django.utils import timezone
        from estado_ordenes.models import EstadoOrden
        from estado_tareas.models import EstadoTarea
        from ordenes.forms import OrdenForm
        from ordenes_trilla.models import OrdenTrilla

        estado_completada_orden = EstadoOrden.objects.create(estado_orden='Completada')
        estado_pendiente_tarea = EstadoTarea.objects.create(estado_tareas='Pendiente')
        orden = Orden.objects.create(
            cliente=self.cliente,
            orden='ORDTRILLAPEND',
            estado_orden=self.estado_orden,
            fecha_inicio_orden=timezone.now(),
            peso_bruto=10,
            peso=10,
            created_at=timezone.now(),
        )
        self._create_child_process(OrdenTrilla, orden, estado_pendiente_tarea)

        form = OrdenForm(
            data=self._completion_data(orden, estado_completada_orden, trilla='on', conf_trilla='on'),
            instance=orden,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('procesos pendientes: Trilla', str(form.non_field_errors()))

    def test_form_bloquea_completada_si_proceso_requerido_no_tiene_registro(self):
        from django.utils import timezone
        from estado_ordenes.models import EstadoOrden
        from ordenes.forms import OrdenForm

        estado_completada_orden = EstadoOrden.objects.create(estado_orden='Completada')
        orden = Orden.objects.create(
            cliente=self.cliente,
            orden='ORDSINTRILLA',
            estado_orden=self.estado_orden,
            fecha_inicio_orden=timezone.now(),
            peso_bruto=10,
            peso=10,
            created_at=timezone.now(),
        )

        form = OrdenForm(
            data=self._completion_data(orden, estado_completada_orden, trilla='on', conf_trilla='on'),
            instance=orden,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('procesos requeridos sin una orden registrada: Trilla', str(form.non_field_errors()))

    def test_form_bloquea_completada_si_uno_de_varios_tuestes_esta_pendiente(self):
        from django.utils import timezone
        from estado_ordenes.models import EstadoOrden
        from estado_tareas.models import EstadoTarea
        from ordenes.forms import OrdenForm
        from tueste.models import Tueste

        estado_completada_orden = EstadoOrden.objects.create(estado_orden='Completada')
        estado_completada_tarea = EstadoTarea.objects.create(estado_tareas='Completada')
        estado_pendiente_tarea = EstadoTarea.objects.create(estado_tareas='Pendiente')
        orden = Orden.objects.create(
            cliente=self.cliente,
            orden='ORDMULTITUESTE',
            estado_orden=self.estado_orden,
            fecha_inicio_orden=timezone.now(),
            peso_bruto=10,
            peso=10,
            created_at=timezone.now(),
        )
        self._create_child_process(Tueste, orden, estado_completada_tarea)
        self._create_child_process(Tueste, orden, estado_pendiente_tarea)

        form = OrdenForm(
            data=self._completion_data(orden, estado_completada_orden, tueste_flag='on', conf_tueste='on'),
            instance=orden,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('procesos pendientes: Tueste', str(form.non_field_errors()))

    def test_form_bloquea_completada_e_informa_varios_procesos_pendientes(self):
        from django.utils import timezone
        from estado_ordenes.models import EstadoOrden
        from estado_tareas.models import EstadoTarea
        from ordenes.forms import OrdenForm
        from tueste.models import Tueste
        from seleccion_tueste.models import SeleccionTueste
        from empaques.models import Empaque

        estado_completada_orden = EstadoOrden.objects.create(estado_orden='Completada')
        estado_pendiente_tarea = EstadoTarea.objects.create(estado_tareas='Pendiente')
        orden = Orden.objects.create(
            cliente=self.cliente,
            orden='ORDVARIOSPEND',
            estado_orden=self.estado_orden,
            fecha_inicio_orden=timezone.now(),
            peso_bruto=10,
            peso=10,
            created_at=timezone.now(),
        )
        for model in (Tueste, SeleccionTueste, Empaque):
            self._create_child_process(model, orden, estado_pendiente_tarea)

        form = OrdenForm(
            data=self._completion_data(
                orden,
                estado_completada_orden,
                tueste_flag='on',
                conf_tueste='on',
                selec_cafe_tostado='on',
                conf_sel_tostado='on',
                empaque_flag='on',
                conf_empaque='on',
            ),
            instance=orden,
        )

        self.assertFalse(form.is_valid())
        error_text = str(form.non_field_errors())
        self.assertIn('Tueste', error_text)
        self.assertIn('Selección Tueste', error_text)
        self.assertIn('Empaque', error_text)

    def test_formset_requiere_al_menos_un_detalle_cuando_trajo_empaque_esta_activo(self):
        from ordenes.forms import build_detalle_empaque_formset

        formset = build_detalle_empaque_formset(data={
            'trabajo_empaque': 'on',
            **self._detalle_management_data(total_forms=1),
        })

        self.assertFalse(formset.is_valid())
        self.assertIn('Debe registrar al menos un detalle de empaque', formset.non_form_errors()[0])

    def test_crea_orden_con_multiples_detalles_empaque_y_sincroniza_fk_legacy(self):
        from cafe_empaque.models import CafeEmpaque
        from tamano_empaque.models import TamanoEmpaque

        empaque_1 = CafeEmpaque.objects.create(empaque_cafe='Bolsa Kraft')
        empaque_2 = CafeEmpaque.objects.create(empaque_cafe='Bolsa Negra')
        tamano_1 = TamanoEmpaque.objects.create(tamano_empaque='250g')
        tamano_2 = TamanoEmpaque.objects.create(tamano_empaque='500g')

        url = reverse('ordenes_produccion_nuevo')
        data = self._base_orden_data(
            orden='ORDPACKGRID01',
            trabajo_empaque='on',
            **self._detalle_management_data(total_forms=3),
            **{
                'detalle_empaque-0-empaque_cafe': str(empaque_1.id),
                'detalle_empaque-0-tamano_empaque': str(tamano_1.id),
                'detalle_empaque-0-cantidad': '10',
                'detalle_empaque-1-empaque_cafe': str(empaque_2.id),
                'detalle_empaque-1-tamano_empaque': str(tamano_2.id),
                'detalle_empaque-1-cantidad': '5',
                'detalle_empaque-2-empaque_cafe': '',
                'detalle_empaque-2-tamano_empaque': '',
                'detalle_empaque-2-cantidad': '',
            },
        )

        response = self.client.post(url, data, follow=True)

        self.assertEqual(response.status_code, 200)
        orden = Orden.objects.get(orden='ORDPACKGRID01')
        detalles = list(orden.detalles_empaque.order_by('id'))

        self.assertEqual(len(detalles), 2)
        self.assertEqual(detalles[0].cantidad, 10)
        self.assertEqual(detalles[1].cantidad, 5)
        self.assertEqual(orden.empaque_cafe_id, empaque_1.id)
        self.assertEqual(orden.tamano_empaque_id, tamano_1.id)

    def test_edicion_orden_limpia_detalle_empaque_cuando_trajo_empaque_se_desactiva(self):
        from cafe_empaque.models import CafeEmpaque
        from tamano_empaque.models import TamanoEmpaque
        from django.utils import timezone

        empaque = CafeEmpaque.objects.create(empaque_cafe='Bolsa Blanca')
        tamano = TamanoEmpaque.objects.create(tamano_empaque='1Kg')
        orden = Orden.objects.create(
            cliente=self.cliente,
            orden='ORDPACKGRID02',
            estado_orden=self.estado_orden,
            fecha_inicio_orden=timezone.now(),
            created_at=timezone.now(),
            trabajo_empaque=True,
            empaque_cafe=empaque,
            tamano_empaque=tamano,
            prioridad=1,
        )
        detalle = DetalleEmpaqueOrden.objects.create(
            orden=orden,
            empaque_cafe=empaque,
            tamano_empaque=tamano,
            cantidad=3,
        )

        url = reverse('ordenes_produccion_editar', args=[orden.id])
        data = self._base_orden_data(
            orden='ORDPACKGRID02',
            trabajo_empaque='',
            prioridad=2,
            **self._detalle_management_data(total_forms=2, initial_forms=1),
            **{
                'detalle_empaque-0-id': str(detalle.id),
                'detalle_empaque-0-empaque_cafe': str(empaque.id),
                'detalle_empaque-0-tamano_empaque': str(tamano.id),
                'detalle_empaque-0-cantidad': '3',
                'detalle_empaque-1-empaque_cafe': '',
                'detalle_empaque-1-tamano_empaque': '',
                'detalle_empaque-1-cantidad': '',
            },
        )

        response = self.client.post(url, data, follow=True)

        self.assertEqual(response.status_code, 200)
        orden.refresh_from_db()
        self.assertFalse(orden.trabajo_empaque)
        self.assertIsNone(orden.empaque_cafe_id)
        self.assertIsNone(orden.tamano_empaque_id)
        self.assertEqual(orden.detalles_empaque.count(), 0)
from django.test import TestCase
from .models import Orden
from clientes.models import Cliente
from empleados.models import Empleado
from inventario_cafe.models import InventarioCafe
from estado_ordenes.models import EstadoOrden
from datetime import datetime

class OrdenCrudSQLServerTest(TestCase):
    reset_sequences = True

    def setUp(self):
        self.cliente = Cliente.objects.create(nombre="Test Cliente")
        self.empleado = Empleado.objects.create(nombres="Test", apellidos="Empleado", identificacion="9999")
        self.inven_cafe = InventarioCafe.objects.create()
        self.estado = EstadoOrden.objects.create(estado_orden="Pendiente")

    def test_crud_ordenes(self):
        # Crear 3 órdenes
        ordenes = []
        for i in range(3):
            orden = Orden.objects.create(
                cliente=self.cliente,
                id_empleado=self.empleado,
                id_inven_cafe=self.inven_cafe,
                estado_orden=self.estado,
                orden=f"ORD{i+1:02d}",
                fecha_inicio_orden=datetime.now(),
                prioridad=i+1,
                notas=f"Nota inicial {i+1}"
            )
            ordenes.append(orden)
        self.assertEqual(Orden.objects.count(), 3)

        # Editar cada orden
        for idx, orden in enumerate(ordenes):
            orden.prioridad = 10 + idx
            orden.notas = f"Editada {idx+1}"
            orden.orden = f"EDITSQL{idx+1}"
            orden.save()

        # Verificar edición
        for idx, orden in enumerate(Orden.objects.all()):
            self.assertEqual(orden.prioridad, 10 + idx)
            self.assertTrue(orden.notas.startswith("Editada"))
            self.assertTrue(orden.orden.startswith("EDITSQL"))

        # Eliminar cada orden
        for orden in ordenes:
            orden.delete()
        self.assertEqual(Orden.objects.count(), 0)


class OrdenModalStructureTests(TestCase):
    def setUp(self):
        from django.utils import timezone


class OrdenPermisosHtmxTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        from seguridad.models import PerfilUsuario, Rol

        self.user = User.objects.create_user(username='programador_sin_permiso', password='testpass')
        self.rol_programador = Rol.objects.create(nombre='Programador')
        PerfilUsuario.objects.create(user=self.user, rol=self.rol_programador)
        self.client.login(username='programador_sin_permiso', password='testpass')

    def test_nueva_orden_sin_permiso_devuelve_modal_html_para_hx_request(self):
        url = reverse('ordenes_produccion_nuevo')
        response = self.client.get(url, HTTP_HX_REQUEST='true')

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'data-modal-root', html=False)
        self.assertContains(response, 'Acceso denegado')
        self.assertContains(response, 'No tienes permiso para realizar esta acción.')
        from empleados.models import Empleado
        from estado_ordenes.models import EstadoOrden
        from inventario_cafe.models import InventarioCafe

        self.cliente = Cliente.objects.create(nombre="Cliente ModalTest")
        self.empleado = Empleado.objects.create(nombres="John", apellidos="Doe", identificacion="MOD1")
        # Algunos campos pueden ser opcionales al renderizar GET del modal
        self.estado = EstadoOrden.objects.create(estado_orden="En Espera")
        self.inv = InventarioCafe.objects.create()

        self.orden = Orden.objects.create(
            cliente=self.cliente,
            id_empleado=self.empleado,
            id_inven_cafe=self.inv,
            estado_orden=self.estado,
            orden="ORDMOD1",
            fecha_inicio_orden=timezone.now(),
            prioridad=1,
        )

    def test_modal_footer_buttons_outside_body(self):
        from django.urls import reverse
        url = reverse('ordenes_produccion_editar', args=[self.orden.id])
        # Solicita el fragmento como lo hace el frontend (AJAX)
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)

        html = resp.content.decode('utf-8', errors='ignore')
        # Presencia de las secciones requeridas
        self.assertIn('data-modal-root', html)
        self.assertIn('modal-head', html)
        self.assertIn('modal-body', html)
        self.assertIn('modal-footer', html)

        body_start = html.find('class="modal-body')
        footer_start = html.find('class="modal-footer')
        self.assertNotEqual(body_start, -1, 'modal-body no encontrado')
        self.assertNotEqual(footer_start, -1, 'modal-footer no encontrado')
        self.assertGreater(footer_start, body_start, 'El footer debe ir después del body')

        body_section = html[body_start:footer_start]
        # No deben existir botones de acción dentro del body
        self.assertNotIn('data-close-modal', body_section)
        self.assertNotIn('type="submit"', body_section)
        self.assertNotIn('btn-primary', body_section)

        # Validar clases de comportamiento (crecen/encogen)
        self.assertIn('shrink-0', html)  # header/footer
        self.assertIn('grow overflow-y-auto', html)  # body scrolleable


class OrdenModalTemplateStaticTest(SimpleTestCase):
    def test_template_has_footer_after_body_and_no_buttons_in_body(self):
        import os
        from pathlib import Path
        # Lee el template directamente del disco para validación estática
        tpl_path = Path(__file__).resolve().parent / 'templates' / 'ordenes' / 'detail_OrdenesProduccion.html'
        self.assertTrue(tpl_path.exists(), f"No se encontró el template en {tpl_path}")
        html = tpl_path.read_text(encoding='utf-8')

        body_start = html.find('class="modal-body')
        footer_start = html.find('class="modal-footer')
        self.assertNotEqual(body_start, -1, 'modal-body no encontrado en template')
        self.assertNotEqual(footer_start, -1, 'modal-footer no encontrado en template')
        self.assertGreater(footer_start, body_start, 'El footer debe ir después del body en el template')

        body_section = html[body_start:footer_start]
        self.assertNotIn('data-close-modal', body_section)
        self.assertNotIn('type="submit"', body_section)
        self.assertNotIn('btn-primary', body_section)
