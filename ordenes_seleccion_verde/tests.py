from django.test import TestCase
from django.utils import timezone

from clientes.models import Cliente
from estado_tareas.models import EstadoTarea
from ordenes.models import Orden
from zaranda_grupo.models import ZarandaGrupo

from .forms import (
    MEDICIONES_CLIENTE_UNICAS_ERROR,
    OrdenSeleccionVerdeForm,
    SELECCION_TIPO_REQUERIDO_ERROR,
)
from .models import OrdenSeleccionVerde


class OrdenSeleccionVerdeFormTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre='Cliente', apellidos='Seleccion Verde')
        self.estado = EstadoTarea.objects.create(estado_tareas='Pendiente')
        self.estado_completada = EstadoTarea.objects.create(estado_tareas='Completada')
        self.orden = Orden.objects.create(
            orden='OP-SV-001',
            cliente=self.cliente,
            selec_cafe_verde=True,
        )
        self.zaranda_grupo = ZarandaGrupo.objects.create(zaranda_grupo='10')
        self.zaranda_na = ZarandaGrupo.objects.create(zaranda_grupo='N/A')

    def _base_data(self):
        return {
            'orden': str(self.orden.pk),
            'estado_tareas': str(self.estado.pk),
            'notas': 'Prueba',
        }

    def test_rechaza_guardado_si_no_selecciona_zaranda_ni_catadora(self):
        form = OrdenSeleccionVerdeForm(data=self._base_data())

        self.assertFalse(form.is_valid())
        self.assertIn(SELECCION_TIPO_REQUERIDO_ERROR, form.non_field_errors())

    def test_permte_guardado_si_selecciona_zaranda(self):
        form = OrdenSeleccionVerdeForm(
            data={
                **self._base_data(),
                'zaranda': 'on',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_pendiente_permite_guardar_zaranda_sin_peso(self):
        form = OrdenSeleccionVerdeForm(
            data={
                **self._base_data(),
                'zaranda': 'on',
                'IdZarandaGrupo1': str(self.zaranda_grupo.pk),
                'peso_grupo1': '',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_completada_exige_peso_si_hay_malla_seleccionada(self):
        form = OrdenSeleccionVerdeForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_completada.pk),
                'zaranda': 'on',
                'IdZarandaGrupo1': str(self.zaranda_grupo.pk),
                'peso_grupo1': '',
                'catadora': 'on',
                'peso_grupo2': '1',
                'peso_grupo3': '1',
                'peso_grupo4': '1',
                'peso_grupo5': '1',
                'peso_grupo_ripio': '1',
                'peso_cat_ripio': '1',
                'peso_cat_balsos': '1',
                'peso_cat_grupo1': '1',
                'peso_cat_grupo2': '1',
                'peso_aceptado': '1',
                'notas': 'Prueba',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('peso_grupo1', form.errors)

    def test_completada_permite_malla_na_con_peso_cero(self):
        form = OrdenSeleccionVerdeForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_completada.pk),
                'zaranda': 'on',
                'IdZarandaGrupo1': str(self.zaranda_na.pk),
                'peso_grupo1': '0',
                'catadora': 'on',
                'notas': 'Prueba',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_completada_exige_peso_cat_ripio_si_catacion_ripio_esta_marcada(self):
        form = OrdenSeleccionVerdeForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_completada.pk),
                'catadora': 'on',
                'catacion_ripio': 'on',
                'peso_cat_ripio': '0',
                'notas': 'Prueba',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('peso_cat_ripio', form.errors)
        self.assertIn('Debe ingresar Peso Cat. Ripio porque Catación Ripio está seleccionada.', form.errors['peso_cat_ripio'])

    def test_completada_exige_peso_cat_balsos_si_catacion_balsos_esta_marcada(self):
        form = OrdenSeleccionVerdeForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_completada.pk),
                'catadora': 'on',
                'catacion_balsos': 'on',
                'peso_cat_balsos': '0',
                'notas': 'Prueba',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('peso_cat_balsos', form.errors)
        self.assertIn('Debe ingresar Peso Cat. Balsos porque Catación Balsos está seleccionada.', form.errors['peso_cat_balsos'])

    def test_completada_exige_peso_cat_grupo1_si_catacion_grupo1_esta_marcada(self):
        form = OrdenSeleccionVerdeForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_completada.pk),
                'catadora': 'on',
                'catacion_grupo1': 'on',
                'peso_cat_grupo1': '0',
                'notas': 'Prueba',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('peso_cat_grupo1', form.errors)
        self.assertIn('Debe ingresar Peso Cat. Grupo 1 porque Catación Grupo 1 está seleccionada.', form.errors['peso_cat_grupo1'])

    def test_completada_exige_peso_cat_grupo2_si_catacion_grupo2_esta_marcada(self):
        form = OrdenSeleccionVerdeForm(
            data={
                'orden': str(self.orden.pk),
                'estado_tareas': str(self.estado_completada.pk),
                'catadora': 'on',
                'catacion_grupo2': 'on',
                'peso_cat_grupo2': '0',
                'notas': 'Prueba',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('peso_cat_grupo2', form.errors)
        self.assertIn('Debe ingresar Peso Cat. Grupo 2 porque Catación Grupo 2 está seleccionada.', form.errors['peso_cat_grupo2'])

    def test_pendiente_permite_cataciones_marcadas_con_peso_cero(self):
        form = OrdenSeleccionVerdeForm(
            data={
                **self._base_data(),
                'catadora': 'on',
                'catacion_ripio': 'on',
                'peso_cat_ripio': '0',
                'catacion_balsos': 'on',
                'peso_cat_balsos': '0',
                'catacion_grupo1': 'on',
                'peso_cat_grupo1': '0',
                'catacion_grupo2': 'on',
                'peso_cat_grupo2': '0',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_edicion_tambien_rechaza_si_quedan_ambas_opciones_desmarcadas(self):
        seleccion = OrdenSeleccionVerde.objects.create(
            orden=self.orden,
            estado_tareas=self.estado,
            zaranda=True,
            catadora=None,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        form = OrdenSeleccionVerdeForm(
            data=self._base_data(),
            instance=seleccion,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(SELECCION_TIPO_REQUERIDO_ERROR, form.non_field_errors())

    def test_edicion_conserva_valores_dependientes_de_checkboxes_marcados(self):
        seleccion = OrdenSeleccionVerde.objects.create(
            orden=self.orden,
            estado_tareas=self.estado,
            catadora=True,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        form = OrdenSeleccionVerdeForm(
            data={
                **self._base_data(),
                'catadora': 'on',
                'catacion_ripio': 'on',
                'peso_cat_ripio': '1',
                'catacion_balsos': 'on',
                'peso_cat_balsos': '2',
                'catacion_grupo1': 'on',
                'peso_cat_grupo1': '3',
                'catacion_grupo2': 'on',
                'peso_cat_grupo2': '4',
                'medir_humedad': 'on',
                'humedad': '10.5',
                'medir_densidad': 'on',
                'densidad': '0.7',
            },
            instance=seleccion,
        )

        self.assertTrue(form.is_valid(), form.errors)
        actualizado = form.save()

        self.assertEqual(actualizado.peso_cat_ripio, 1)
        self.assertEqual(actualizado.peso_cat_balsos, 2)
        self.assertEqual(actualizado.peso_cat_grupo1, 3)
        self.assertEqual(actualizado.peso_cat_grupo2, 4)
        self.assertEqual(actualizado.humedad, 10.5)
        self.assertEqual(actualizado.densidad, 0.7)

    def test_edicion_limpia_valores_dependientes_de_checkboxes_desmarcados(self):
        seleccion = OrdenSeleccionVerde.objects.create(
            orden=self.orden,
            estado_tareas=self.estado,
            catadora=True,
            catacion_ripio=True,
            peso_cat_ripio=1,
            catacion_balsos=True,
            peso_cat_balsos=2,
            catacion_grupo1=True,
            peso_cat_grupo1=3,
            catacion_grupo2=True,
            peso_cat_grupo2=4,
            medir_humedad=True,
            humedad=10.5,
            medir_densidad=True,
            densidad=0.7,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        form = OrdenSeleccionVerdeForm(
            data={
                **self._base_data(),
                'catadora': 'on',
            },
            instance=seleccion,
        )

        self.assertTrue(form.is_valid(), form.errors)
        actualizado = form.save()

        self.assertFalse(actualizado.catacion_ripio)
        self.assertFalse(actualizado.catacion_balsos)
        self.assertFalse(actualizado.catacion_grupo1)
        self.assertFalse(actualizado.catacion_grupo2)
        self.assertFalse(actualizado.medir_humedad)
        self.assertFalse(actualizado.medir_densidad)
        self.assertIsNone(actualizado.peso_cat_ripio)
        self.assertIsNone(actualizado.peso_cat_balsos)
        self.assertIsNone(actualizado.peso_cat_grupo1)
        self.assertIsNone(actualizado.peso_cat_grupo2)
        self.assertIsNone(actualizado.humedad)
        self.assertIsNone(actualizado.densidad)

    def test_otro_registro_del_mismo_cliente_bloquea_humedad_y_densidad(self):
        OrdenSeleccionVerde.objects.create(
            orden=self.orden,
            estado_tareas=self.estado,
            catadora=True,
            medir_humedad=True,
            humedad=10.5,
            medir_densidad=True,
            densidad=700,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        otra_orden = Orden.objects.create(
            orden='OP-SV-002',
            cliente=self.cliente,
            selec_cafe_verde=True,
        )

        form_inicial = OrdenSeleccionVerdeForm(data={
            'orden': str(otra_orden.pk),
            'estado_tareas': str(self.estado.pk),
            'catadora': 'on',
        })
        self.assertTrue(form_inicial.mediciones_cliente_bloqueadas)
        for campo in ('medir_humedad', 'humedad', 'medir_densidad', 'densidad'):
            self.assertTrue(form_inicial.fields[campo].disabled)

        form = OrdenSeleccionVerdeForm(data={
            'orden': str(otra_orden.pk),
            'estado_tareas': str(self.estado.pk),
            'catadora': 'on',
            'medir_humedad': 'on',
            'humedad': '11',
            'medir_densidad': 'on',
            'densidad': '710',
        })
        self.assertFalse(form.is_valid())
        self.assertIn(MEDICIONES_CLIENTE_UNICAS_ERROR, form.non_field_errors())

    def test_registro_que_tiene_las_mediciones_puede_editarlas(self):
        seleccion = OrdenSeleccionVerde.objects.create(
            orden=self.orden,
            estado_tareas=self.estado,
            catadora=True,
            medir_humedad=True,
            humedad=10.5,
            medir_densidad=True,
            densidad=700,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        form = OrdenSeleccionVerdeForm(instance=seleccion)

        self.assertFalse(form.mediciones_cliente_bloqueadas)
        for campo in ('medir_humedad', 'humedad', 'medir_densidad', 'densidad'):
            self.assertFalse(form.fields[campo].disabled)
