from django.test import TestCase

from clientes.models import Cliente
from proceso_inven_cafe.models import ProcesoInvenCafe

from .forms import CalidadForm, TIEMPOS_TOSTION
from .models import Calidad


class CalidadFormTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre='Cliente Calidad')
        self.proceso = ProcesoInvenCafe.objects.create(proceso_inven_cafe='Lavado')

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
            'temperatura_19': '205',
            'evento_19': 'Fin',
        })

        self.assertTrue(form.is_valid(), form.errors)
        registro = form.save()
        self.assertEqual(registro.orden, 'ORDEN ESCRITA A MANO')
        self.assertIsNotNone(registro.fecha_ingreso)
        self.assertEqual(registro.lecturas_tostion[0]['tiempo'], '0:00')
        self.assertEqual(registro.lecturas_tostion[-1]['tiempo'], '9:30')
        self.assertEqual(Calidad._meta.db_table, 'tblcalidad')

    def test_edicion_recupera_lecturas_y_conserva_fecha_ingreso(self):
        registro = Calidad.objects.create(
            cliente=self.cliente,
            proceso=self.proceso,
            orden='123',
            tostion_json='[{"tiempo":"0:30","temperatura":170,"evento":"Inicio"}]',
        )
        fecha_original = registro.fecha_ingreso
        form = CalidadForm(instance=registro)

        self.assertEqual(len(form.tostion_filas), len(TIEMPOS_TOSTION))
        self.assertEqual(form['temperatura_1'].value(), 170)
        self.assertNotIn('fecha_ingreso', form.fields)

        form = CalidadForm(data={
            'cliente': self.cliente.pk,
            'proceso': self.proceso.pk,
            'orden': '123 corregida',
            'temperatura_1': '175',
            'evento_1': 'Inicio',
        }, instance=registro)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        registro.refresh_from_db()
        self.assertEqual(registro.fecha_ingreso, fecha_original)
        self.assertEqual(registro.lecturas_tostion[0]['temperatura'], 175)
