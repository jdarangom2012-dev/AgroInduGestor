from datetime import date, datetime
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.urls import reverse

from .calidad_pdf import render_calidad_pdf


class ReporteCalidadTests(SimpleTestCase):
    def test_rutas_requieren_autenticacion(self):
        for name in ('reportes_calidad', 'reportes_calidad_pdf'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response['Location'])

    def test_pdf_contiene_muestra_y_soporta_lecturas(self):
        cliente = SimpleNamespace(__str__=lambda self: 'Cliente de prueba')
        registro = SimpleNamespace(
            pk=1, muestra_numero='M-1', orden='ORD-1',
            fecha_ingreso=datetime(2026, 9, 19, 10, 30), fecha_recibido=date(2026, 9, 18),
            sencilla=True, q_grader=False, variedad='Bourbon', proceso='Lavado', origen='Antioquia',
            altura=1800, peso_pergamino=10, peso_verde=8, peso_excelsio=7,
            humedad=11, densidad=700, factor=90, peso_tostado=6,
            notas='Nota de prueba', observaciones='Observación final',
            lecturas_tostion=[{'tiempo': '0:00', 'temperatura': 180, 'evento': 'Inicio'}],
        )
        pdf = render_calidad_pdf(cliente, [registro])
        self.assertTrue(pdf.startswith(b'%PDF'))

    def test_pdf_sin_muestras(self):
        pdf = render_calidad_pdf('Cliente sin muestras', [])
        self.assertTrue(pdf.startswith(b'%PDF'))
