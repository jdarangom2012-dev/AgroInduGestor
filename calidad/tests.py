from django import forms
from django.test import TestCase

from clientes.models import Cliente
from origen_cafe.models import OrigenCafe
from proceso_inven_cafe.models import ProcesoInvenCafe
from variedad_cafe.models import VariedadCafe

from .forms import CalidadForm, TIEMPOS_TOSTION
from .models import Calidad


class CalidadFormTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre='Cliente Calidad')
        self.proceso = ProcesoInvenCafe.objects.create(proceso_inven_cafe='Lavado')
        self.origen = OrigenCafe.objects.create(origen='Antioquia')
        self.variedad = VariedadCafe.objects.create(variedad_cafe='Bourbon')

    def test_formulario_guarda_orden_libre_fecha_sistema_y_tostion(self):
        form = CalidadForm(data={
            'cliente': self.cliente.pk,
            'proceso': self.proceso.pk,
            'orden': 'ORDEN ESCRITA A MANO',
            'fecha_recibido': '2026-09-19',
            'muestra_numero': 'M-1',
            'peso_verde': '10.5',
            'temperatura_0': '180',
            'evento_0': 'Carga',
            'potencia_gas_0': '75',
            'potencia_aire_0': '40',
            'temperatura_19': '205',
            'evento_19': 'Fin',
        })

        self.assertTrue(form.is_valid(), form.errors)
        registro = form.save()
        self.assertEqual(registro.orden, 'ORDEN ESCRITA A MANO')
        self.assertIsNotNone(registro.fecha_ingreso)
        self.assertEqual(registro.lecturas_tostion[0]['tiempo'], '0:00')
        self.assertEqual(registro.lecturas_tostion[0]['potencia_gas'], 75)
        self.assertEqual(registro.lecturas_tostion[0]['potencia_aire'], 40)
        self.assertEqual(registro.lecturas_tostion[-1]['tiempo'], '9:30')
        self.assertEqual(Calidad._meta.db_table, 'tblcalidad')

    def test_edicion_recupera_lecturas_y_conserva_fecha_ingreso(self):
        registro = Calidad.objects.create(
            cliente=self.cliente,
            proceso=self.proceso,
            orden='123',
            tostion_json='[{"tiempo":"0:30","temperatura":170,"evento":"Inicio","potencia_gas":60,"potencia_aire":35}]',
        )
        fecha_original = registro.fecha_ingreso
        form = CalidadForm(instance=registro)

        self.assertEqual(len(form.tostion_filas), len(TIEMPOS_TOSTION))
        self.assertEqual(form['temperatura_1'].value(), 170)
        self.assertEqual(form['potencia_gas_1'].value(), 60)
        self.assertEqual(form['potencia_aire_1'].value(), 35)
        self.assertNotIn('fecha_ingreso', form.fields)

        form = CalidadForm(data={
            'cliente': self.cliente.pk,
            'proceso': self.proceso.pk,
            'orden': '123 corregida',
            'temperatura_1': '175',
            'evento_1': 'Inicio',
            'potencia_gas_1': '65',
            'potencia_aire_1': '38',
        }, instance=registro)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        registro.refresh_from_db()
        self.assertEqual(registro.fecha_ingreso, fecha_original)
        self.assertEqual(registro.lecturas_tostion[0]['temperatura'], 175)
        self.assertEqual(registro.lecturas_tostion[0]['potencia_gas'], 65)
        self.assertEqual(registro.lecturas_tostion[0]['potencia_aire'], 38)

    def test_potencias_solo_aceptan_enteros_no_negativos(self):
        datos_base = {
            'cliente': self.cliente.pk,
            'proceso': self.proceso.pk,
            'orden': 'CAL-POTENCIA',
        }
        decimal = CalidadForm(data={**datos_base, 'potencia_gas_0': '10.5'})
        negativo = CalidadForm(data={**datos_base, 'potencia_aire_0': '-1'})

        self.assertFalse(decimal.is_valid())
        self.assertIn('potencia_gas_0', decimal.errors)
        self.assertFalse(negativo.is_valid())
        self.assertIn('potencia_aire_0', negativo.errors)

    def test_variedad_y_origen_son_listas_cargadas_desde_maestros(self):
        form = CalidadForm()

        self.assertIsInstance(form.fields['variedad'].widget, forms.Select)
        self.assertIsInstance(form.fields['origen'].widget, forms.Select)
        self.assertIn(('Bourbon', 'Bourbon'), list(form.fields['variedad'].choices))
        self.assertIn(('Antioquia', 'Antioquia'), list(form.fields['origen'].choices))
        self.assertEqual(form.fields['variedad'].widget.attrs['class'], 'w-full select')
        self.assertEqual(form.fields['origen'].widget.attrs['class'], 'w-full select')

    def test_rechaza_valores_que_no_existen_en_los_maestros(self):
        form = CalidadForm(data={
            'cliente': self.cliente.pk,
            'proceso': self.proceso.pk,
            'orden': 'CAL-1',
            'variedad': 'Variedad inventada',
            'origen': 'Origen inventado',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('variedad', form.errors)
        self.assertIn('origen', form.errors)

    def test_guarda_y_recupera_selecciones_de_los_maestros(self):
        form = CalidadForm(data={
            'cliente': self.cliente.pk,
            'proceso': self.proceso.pk,
            'orden': 'CAL-2',
            'variedad': 'Bourbon',
            'origen': 'Antioquia',
        })
        self.assertTrue(form.is_valid(), form.errors)
        registro = form.save()

        form_edicion = CalidadForm(instance=registro)
        self.assertEqual(form_edicion['variedad'].value(), 'Bourbon')
        self.assertEqual(form_edicion['origen'].value(), 'Antioquia')

    def test_edicion_conserva_valores_historicos_fuera_del_maestro(self):
        registro = Calidad.objects.create(
            cliente=self.cliente,
            proceso=self.proceso,
            orden='CAL-HIST',
            variedad='Variedad antigua',
            origen='Origen antiguo',
        )

        form = CalidadForm(instance=registro)

        self.assertEqual(form['variedad'].value(), 'Variedad antigua')
        self.assertEqual(form['origen'].value(), 'Origen antiguo')
        self.assertIn(
            ('Variedad antigua', 'Variedad antigua (valor histórico)'),
            list(form.fields['variedad'].choices),
        )
        self.assertIn(
            ('Origen antiguo', 'Origen antiguo (valor histórico)'),
            list(form.fields['origen'].choices),
        )
