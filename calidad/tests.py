from decimal import Decimal
from datetime import date

from django import forms
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from clientes.models import Cliente
from origen_cafe.models import OrigenCafe
from proceso_inven_cafe.models import ProcesoInvenCafe
from variedad_cafe.models import VariedadCafe

from .forms import AnalisisSensorialForm, CalidadForm, TIEMPOS_TOSTION
from .models import AnalisisSensorial, Calidad
from reportes.sensorial_pdf import render_analisis_sensorial_pdf


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
            'peso_defecto': '2.75',
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
        self.assertEqual(registro.peso_defecto, 2.75)
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

    def test_peso_defecto_no_admite_valores_negativos(self):
        form = CalidadForm(data={
            'cliente': self.cliente.pk,
            'proceso': self.proceso.pk,
            'orden': 'CAL-DEFECTO',
            'peso_defecto': '-0.5',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('peso_defecto', form.errors)

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


class AnalisisSensorialFormTests(TestCase):
    def datos_validos(self, **cambios):
        datos = {
            'nombre': 'Hafid Vélez', 'fecha': '2026-09-08',
            'objetivo': 'Perfilar muestra', 'muestra_numero': 'Indómito',
            'nivel_tueste': '6', 'intensidad_fragancia': '5', 'intensidad_aroma': '5',
            'descriptores_fragancia_aroma': ['afrutado', 'citricos'],
            'intensidad_sabor': '6', 'intensidad_sabor_residual': '6',
            'descriptores_sabor': ['dulce', 'cacao'],
            'gustos_predominantes': ['acido', 'dulce'],
            'intensidad_acidez': '7', 'intensidad_dulzor': '6',
            'intensidad_sensacion_boca': '6', 'sensaciones_boca': ['suave'],
            'calidad_fragancia': '6', 'calidad_aroma': '6', 'calidad_sabor': '6',
            'calidad_sabor_residual': '6', 'calidad_acidez': '6', 'calidad_dulzor': '6',
            'calidad_sensacion_boca': '6', 'impresion_global': '6',
            'puntaje_total': '84.25', 'tazas_no_uniformes': '0',
            'tazas_defectuosas': '0', 'defectos_haberlo': ['fenolico'],
        }
        datos.update(cambios)
        return datos

    def test_guarda_listas_y_recupera_selecciones_en_edicion(self):
        form = AnalisisSensorialForm(data=self.datos_validos())
        self.assertTrue(form.is_valid(), form.errors)
        registro = form.save()

        self.assertEqual(registro.lista_descriptores_fragancia_aroma, ['afrutado', 'citricos'])
        self.assertEqual(registro.lista_gustos_predominantes, ['acido', 'dulce'])
        self.assertEqual(registro.lista_defectos_haberlo, ['fenolico'])
        self.assertEqual(registro.puntaje_total, Decimal('89'))
        edicion = AnalisisSensorialForm(instance=registro)
        self.assertEqual(edicion['gustos_predominantes'].value(), ['acido', 'dulce'])
        self.assertEqual(AnalisisSensorial._meta.db_table, 'tblAnalisisSensorial')

    def test_intensidades_se_muestran_como_barras_de_calor(self):
        form = AnalisisSensorialForm()
        for nombre in (
            'intensidad_fragancia', 'intensidad_aroma', 'intensidad_sabor',
            'intensidad_sabor_residual', 'intensidad_acidez', 'intensidad_dulzor',
            'intensidad_sensacion_boca',
        ):
            widget = form.fields[nombre].widget
            self.assertEqual(widget.input_type, 'range')
            self.assertEqual(widget.attrs['min'], '0')
            self.assertEqual(widget.attrs['max'], '15')
            self.assertEqual(widget.attrs['step'], '0.5')
            self.assertEqual(widget.attrs['data-sensory-heatmap'], 'true')

    def test_puntaje_total_no_se_puede_modificar_manualmente(self):
        form = AnalisisSensorialForm(data=self.datos_validos(puntaje_total='999'))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['puntaje_total'], Decimal('89'))
        self.assertTrue(form.fields['puntaje_total'].disabled)
        self.assertEqual(form.fields['puntaje_total'].widget.input_type, 'text')

    def test_puntaje_total_conserva_sumas_decimales(self):
        form = AnalisisSensorialForm(data=self.datos_validos(
            intensidad_fragancia='5.5',
            puntaje_total='',
        ))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['puntaje_total'], Decimal('89.5'))

    def test_limita_gustos_predominantes_a_dos(self):
        form = AnalisisSensorialForm(data=self.datos_validos(
            gustos_predominantes=['acido', 'dulce', 'amargo'],
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('gustos_predominantes', form.errors)

    def test_valida_rangos_del_formato(self):
        form = AnalisisSensorialForm(data=self.datos_validos(
            intensidad_acidez='16', calidad_acidez='10', tazas_defectuosas='6',
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('intensidad_acidez', form.errors)
        self.assertIn('calidad_acidez', form.errors)
        self.assertIn('tazas_defectuosas', form.errors)


class AnalisisSensorialRutasTests(SimpleTestCase):
    def test_rutas_crud(self):
        self.assertEqual(reverse('analisis_sensorial_listar'), '/calidad/analisis-sensorial/')
        self.assertEqual(reverse('analisis_sensorial_nuevo'), '/calidad/analisis-sensorial/nuevo/')
        self.assertEqual(reverse('analisis_sensorial_editar', args=[7]), '/calidad/analisis-sensorial/7/editar/')
        self.assertEqual(reverse('analisis_sensorial_pdf', args=[7]), '/calidad/analisis-sensorial/7/pdf/')
        self.assertEqual(reverse('analisis_sensorial_eliminar', args=[7]), '/calidad/analisis-sensorial/7/eliminar/')


class AnalisisSensorialPdfTests(SimpleTestCase):
    def test_pdf_incluye_datos_y_puntaje(self):
        registro = AnalisisSensorial(
            nombre='Hafid Vélez', fecha=date(2026, 9, 8), objetivo='Perfilar muestra',
            muestra_numero='Indómito', intensidad_fragancia='5.5', intensidad_aroma='8',
            descriptores_fragancia_aroma='["afrutado", "citricos"]',
            calidad_fragancia=7, impresion_global=8, puntaje_total='89.5',
        )

        pdf = render_analisis_sensorial_pdf(registro)

        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertGreater(len(pdf), 3000)
