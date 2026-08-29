from io import BytesIO

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cafe_empaque.models import CafeEmpaque
from clientes.models import Cliente
from empaques.models import DetalleEmpaque, Empaque
from estado_ordenes.models import EstadoOrden
from estado_tareas.models import EstadoTarea
from nivel_molienda.models import NivelMolienda
from nivel_tueste.models import NivelTueste
from ordenes.models import DetalleEmpaqueOrden, Orden
from ordenes_seleccion_tostado.models import OrdenSeleccionTostado
from ordenes_seleccion_verde.models import OrdenSeleccionVerde
from ordenes_trilla.models import OrdenTrilla
from reportes.pdf import render_facturacion_pdf
from reportes.services.facturacion import get_facturacion_report, get_facturacion_report_by_id
from seleccion_tueste.models import SeleccionTueste
from tamano_empaque.models import TamanoEmpaque
from tueste.models import DetalleTueste, Tueste


class FacturacionReportTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre="Cliente", apellidos="Facturacion")
        self.estado_orden = EstadoOrden.objects.create(estado_orden="Pendiente")
        self.estado_orden_completada = EstadoOrden.objects.create(estado_orden="Completada")
        self.estado_completada = EstadoTarea.objects.create(estado_tareas="Completada")
        self.estado_pendiente = EstadoTarea.objects.create(estado_tareas="Pendiente")
        self.empaque_cafe = CafeEmpaque.objects.create(empaque_cafe="Bolsa Tricapa Blanca")
        self.empaque_cafe_2 = CafeEmpaque.objects.create(empaque_cafe="Bolsa Granel Plastica")
        self.tamano = TamanoEmpaque.objects.create(tamano_empaque="500 gr")
        self.tamano_2 = TamanoEmpaque.objects.create(tamano_empaque="1000 gr")
        self.molienda = NivelMolienda.objects.create(nivel_molienda="Media")
        self.nivel_tueste = NivelTueste.objects.create(nivel_tueste="Medio")
        self.user = User.objects.create_user(username="reportes", password="secret")

    def create_order(self, orden="2319", **kwargs):
        defaults = {
            "orden": orden,
            "cliente": self.cliente,
            "estado_orden": self.estado_orden,
            "fecha_inicio_orden": timezone.now(),
            "trilla": True,
            "selec_cafe_verde": True,
            "tueste_flag": True,
            "selec_cafe_tostado": True,
            "empaque_flag": True,
            "trabajo_empaque": True,
            "etiqueta_invima": True,
        }
        defaults.update(kwargs)
        return Orden.objects.create(**defaults)

    def test_consulta_orden_existente(self):
        orden = self.create_order()

        report = get_facturacion_report("2319")

        self.assertEqual(report["orden"], orden)
        self.assertFalse(report["not_found"])

    def test_orden_inexistente(self):
        report = get_facturacion_report("NO-EXISTE")

        self.assertIsNone(report["orden"])
        self.assertTrue(report["not_found"])

    def test_orden_sin_procesos(self):
        self.create_order(
            trilla=False,
            selec_cafe_verde=False,
            tueste_flag=False,
            selec_cafe_tostado=False,
            empaque_flag=False,
            trabajo_empaque=False,
        )

        report = get_facturacion_report("2319")

        self.assertFalse(report["procesos"]["trilla"]["aplica"])
        self.assertFalse(report["procesos"]["seleccion_verde"]["aplica"])
        self.assertFalse(report["procesos"]["tueste"]["aplica"])
        self.assertFalse(report["procesos"]["seleccion_tostado"]["aplica"])
        self.assertFalse(report["procesos"]["empaque"]["aplica"])

    def test_orden_con_trilla_completada(self):
        orden = self.create_order()
        OrdenTrilla.objects.create(
            orden=orden,
            cliente=self.cliente,
            estado_tareas=self.estado_completada,
            peso_cafe_bruto=120,
            peso_cafe_verde=95,
            created_at=timezone.now(),
        )

        trilla = get_facturacion_report("2319")["procesos"]["trilla"]

        self.assertEqual(trilla["entrada"], 120)
        self.assertEqual(trilla["salida"], 95)

    def test_multiples_trillas_completadas_se_suman(self):
        orden = self.create_order()
        for entrada, salida in ((100, 80), (50, 42)):
            OrdenTrilla.objects.create(
                orden=orden,
                cliente=self.cliente,
                estado_tareas=self.estado_completada,
                peso_cafe_bruto=entrada,
                peso_cafe_verde=salida,
                created_at=timezone.now(),
            )

        trilla = get_facturacion_report("2319")["procesos"]["trilla"]

        self.assertEqual(trilla["entrada"], 150)
        self.assertEqual(trilla["salida"], 122)

    def test_excluye_trillas_pendientes(self):
        orden = self.create_order()
        OrdenTrilla.objects.create(
            orden=orden,
            cliente=self.cliente,
            estado_tareas=self.estado_completada,
            peso_cafe_bruto=100,
            peso_cafe_verde=80,
            created_at=timezone.now(),
        )
        OrdenTrilla.objects.create(
            orden=orden,
            cliente=self.cliente,
            estado_tareas=self.estado_pendiente,
            peso_cafe_bruto=999,
            peso_cafe_verde=999,
            created_at=timezone.now(),
        )

        trilla = get_facturacion_report("2319")["procesos"]["trilla"]

        self.assertEqual(trilla["entrada"], 100)
        self.assertEqual(trilla["salida"], 80)

    def test_tueste_con_multiples_batches(self):
        orden = self.create_order()
        tueste = Tueste.objects.create(
            orden=orden,
            estado_tareas=self.estado_completada,
            nivel_tueste=self.nivel_tueste,
            peso_cafe_vede_total=30,
            peso_cafe_tostado_total=25,
            created_at=timezone.now(),
        )
        for numero, kilos in ((1, 12), (2, 18)):
            DetalleTueste.objects.create(
                tueste=tueste,
                numero_batch=numero,
                kilos_verde=kilos,
                kilos_tostado=kilos - 2,
            )

        tueste_section = get_facturacion_report("2319")["procesos"]["tueste"]

        self.assertEqual(tueste_section["entrada"], 30)
        self.assertEqual(tueste_section["salida"], 25)

    def test_seleccion_verde_entrada_sale_de_trilla_y_suma_peso_aceptado(self):
        orden = self.create_order()
        OrdenTrilla.objects.create(
            orden=orden,
            cliente=self.cliente,
            estado_tareas=self.estado_completada,
            peso_cafe_bruto=100,
            peso_cafe_verde=83,
            created_at=timezone.now(),
        )
        OrdenSeleccionVerde.objects.create(
            orden=orden,
            estado_tareas=self.estado_completada,
            peso_grupo1=20,
            peso_grupo2=10,
            peso_grupo3=5,
            peso_grupo4=2,
            peso_grupo5=None,
            peso_grupo_ripio=1,
            peso_cat_ripio=1,
            peso_cat_balsos=2,
            peso_cat_grupo1=20,
            peso_cat_grupo2=20,
            peso_aceptado=75,
            humedad=10.5,
            densidad=750,
            created_at=timezone.now(),
        )
        OrdenSeleccionVerde.objects.create(
            orden=orden,
            estado_tareas=self.estado_completada,
            peso_grupo1=10,
            peso_grupo2=5,
            peso_grupo3=2,
            peso_grupo4=1,
            peso_grupo5=0,
            peso_grupo_ripio=1,
            peso_cat_ripio=2,
            peso_cat_balsos=1,
            peso_cat_grupo1=5,
            peso_cat_grupo2=10,
            peso_aceptado=5,
            humedad=11,
            densidad=730,
            created_at=timezone.now(),
        )

        seleccion = get_facturacion_report("2319")["procesos"]["seleccion_verde"]

        self.assertEqual(seleccion["entrada"], 83)
        self.assertEqual(seleccion["total_de_grupo"], 61)
        self.assertEqual(seleccion["peso_aceptado"], 80)
        self.assertEqual(seleccion["humedad"], 10.75)
        self.assertEqual(seleccion["densidad"], 740)

    def test_seleccion_verde_usa_pesos_catadora_para_total_de_grupo(self):
        orden = self.create_order()
        OrdenSeleccionVerde.objects.create(
            orden=orden,
            estado_tareas=self.estado_completada,
            peso_grupo1=1,
            peso_grupo2=1,
            peso_grupo3=1,
            peso_grupo4=1,
            peso_grupo5=0,
            peso_grupo_ripio=1,
            peso_cat_ripio=1,
            peso_cat_balsos=1,
            peso_cat_grupo1=1,
            peso_cat_grupo2=1,
            peso_aceptado=2,
            humedad=11,
            densidad=700,
            created_at=timezone.now(),
        )

        seleccion = get_facturacion_report("2319")["procesos"]["seleccion_verde"]

        self.assertEqual(seleccion["total_de_grupo"], 4)
        self.assertEqual(seleccion["humedad"], 11)
        self.assertEqual(seleccion["densidad"], 700)
        self.assertNotIn("total_grupo1", seleccion)
        self.assertNotIn("total_grupo2", seleccion)

    def test_seleccion_verde_incluye_totales_de_registros_pendientes(self):
        orden = self.create_order()
        OrdenSeleccionVerde.objects.create(
            orden=orden,
            estado_tareas=self.estado_pendiente,
            peso_cat_ripio=0.62,
            peso_cat_grupo1=1.49,
            peso_cat_grupo2=1.25,
            peso_aceptado=82,
            created_at=timezone.now(),
        )

        seleccion = get_facturacion_report("2319")["procesos"]["seleccion_verde"]

        self.assertEqual(seleccion["total_de_grupo"], 3.36)
        self.assertEqual(seleccion["peso_aceptado"], 82)

    def test_seleccion_verde_promedio_ignora_mediciones_nulas(self):
        orden = self.create_order()
        for humedad, densidad in ((10.5, 750), (None, None)):
            OrdenSeleccionVerde.objects.create(
                orden=orden,
                estado_tareas=self.estado_completada,
                humedad=humedad,
                densidad=densidad,
                created_at=timezone.now(),
            )

        seleccion = get_facturacion_report("2319")["procesos"]["seleccion_verde"]

        self.assertEqual(seleccion["humedad"], 10.5)
        self.assertEqual(seleccion["densidad"], 750)

    def test_seleccion_verde_promedio_excluye_registros_pendientes(self):
        orden = self.create_order()
        OrdenSeleccionVerde.objects.create(
            orden=orden,
            estado_tareas=self.estado_completada,
            humedad=10.5,
            densidad=750,
            created_at=timezone.now(),
        )
        OrdenSeleccionVerde.objects.create(
            orden=orden,
            estado_tareas=self.estado_pendiente,
            humedad=99,
            densidad=999,
            created_at=timezone.now(),
        )

        seleccion = get_facturacion_report("2319")["procesos"]["seleccion_verde"]

        self.assertEqual(seleccion["humedad"], 10.5)
        self.assertEqual(seleccion["densidad"], 750)

    def test_seleccion_verde_usa_mediciones_disponibles_del_mismo_cliente(self):
        self.create_order()
        otra_orden = Orden.objects.create(
            orden="OP-CLIENTE-MEDICIONES",
            cliente=self.cliente,
            selec_cafe_verde=True,
        )
        estado_pendiente = EstadoTarea.objects.create(estado_tareas="Pendiente medición")
        OrdenSeleccionVerde.objects.create(
            orden=otra_orden,
            estado_tareas=estado_pendiente,
            medir_humedad=True,
            humedad=12,
            medir_densidad=True,
            densidad=700,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        seleccion = get_facturacion_report("2319")["procesos"]["seleccion_verde"]

        self.assertEqual(seleccion["humedad"], 12)
        self.assertEqual(seleccion["densidad"], 700)

    def test_reporte_consolida_multiples_registros_por_orden_y_pdf_comparte_contexto(self):
        orden = self.create_order()

        for entrada, salida in ((42, 30), (48, 35)):
            OrdenTrilla.objects.create(
                orden=orden,
                cliente=self.cliente,
                estado_tareas=self.estado_completada,
                peso_cafe_bruto=entrada,
                peso_cafe_verde=salida,
                created_at=timezone.now(),
            )

        for data in (
            {
                "peso_grupo1": 20,
                "peso_grupo2": 10,
                "peso_grupo3": 5,
                "peso_grupo4": 2,
                "peso_grupo5": 0,
                "peso_grupo_ripio": 1,
                "peso_cat_ripio": 1,
                "peso_cat_balsos": 2,
                "peso_cat_grupo1": 20,
                "peso_cat_grupo2": 20,
                "peso_aceptado": 20,
                "humedad": 10.5,
                "densidad": 750,
            },
            {
                "peso_grupo1": 10,
                "peso_grupo2": 5,
                "peso_grupo3": 2,
                "peso_grupo4": 1,
                "peso_grupo5": 0,
                "peso_grupo_ripio": 1,
                "peso_cat_ripio": 2,
                "peso_cat_balsos": 1,
                "peso_cat_grupo1": 5,
                "peso_cat_grupo2": 10,
                "peso_aceptado": 15,
                "humedad": 11,
                "densidad": 730,
            },
        ):
            OrdenSeleccionVerde.objects.create(
                orden=orden,
                estado_tareas=self.estado_completada,
                created_at=timezone.now(),
                **data,
            )

        for verde, tostado in ((40, 32), (50, 39)):
            Tueste.objects.create(
                orden=orden,
                estado_tareas=self.estado_completada,
                nivel_tueste=self.nivel_tueste,
                peso_cafe_vede_total=verde,
                peso_cafe_tostado_total=tostado,
                created_at=timezone.now(),
            )

        for quaker, grupo1, grupo2, grupo3 in ((2.5, 12, 10, 3), (1, 5, 4, 2)):
            SeleccionTueste.objects.create(
                orden=orden,
                estado_tareas=self.estado_pendiente,
                peso_quaker=quaker,
                peso_grupo1=grupo1,
                peso_grupo2=grupo2,
                peso_grupo3=grupo3,
                created_at=timezone.now(),
            )

        html_report = get_facturacion_report("2319")
        pdf_report = get_facturacion_report_by_id(orden.id)

        self.assertEqual(html_report["procesos"], pdf_report["procesos"])

        trilla = html_report["procesos"]["trilla"]
        self.assertEqual(trilla["entrada"], 90)
        self.assertEqual(trilla["salida"], 65)

        seleccion_verde = html_report["procesos"]["seleccion_verde"]
        self.assertEqual(seleccion_verde["total_de_grupo"], 61)
        self.assertEqual(seleccion_verde["peso_aceptado"], 35)
        self.assertEqual(seleccion_verde["humedad"], 10.75)
        self.assertEqual(seleccion_verde["densidad"], 740)

        tueste = html_report["procesos"]["tueste"]
        self.assertEqual(tueste["entrada"], 90)
        self.assertEqual(tueste["salida"], 71)

        seleccion_tueste = html_report["procesos"]["seleccion_tostado"]
        self.assertEqual(seleccion_tueste["peso_quaker"], 3.5)
        self.assertEqual(seleccion_tueste["peso_grupo1"], 17)
        self.assertEqual(seleccion_tueste["peso_grupo2"], 14)
        self.assertEqual(seleccion_tueste["peso_grupo3"], 5)
        self.assertEqual(seleccion_tueste["total_registrado"], 39.5)

    def test_seleccion_tostado_consolida_seleccion_tueste_por_fk_no_por_numero(self):
        orden = self.create_order(id=106)
        SeleccionTueste.objects.create(
            orden=orden,
            estado_tareas=self.estado_pendiente,
            peso_quaker=2.5,
            peso_grupo1=5,
            peso_grupo2=10,
            peso_grupo3=None,
            created_at=timezone.now(),
        )
        SeleccionTueste.objects.create(
            orden=orden,
            estado_tareas=self.estado_completada,
            peso_quaker=None,
            peso_grupo1=1,
            peso_grupo2=2,
            peso_grupo3=3,
            created_at=timezone.now(),
        )
        OrdenSeleccionTostado.objects.create(
            orden=orden,
            estado_tareas=self.estado_orden_completada,
            peso_quaker=100,
            peso_grupo1=100,
            peso_grupo2=100,
            peso_grupo3=100,
            created_at=timezone.now(),
        )

        seleccion = get_facturacion_report("2319")["procesos"]["seleccion_tostado"]

        self.assertEqual(orden.pk, 106)
        self.assertEqual(orden.orden, "2319")
        self.assertEqual(seleccion["peso_quaker"], 2.5)
        self.assertEqual(seleccion["peso_grupo1"], 6)
        self.assertEqual(seleccion["peso_grupo2"], 12)
        self.assertEqual(seleccion["peso_grupo3"], 3)
        self.assertEqual(seleccion["total_registrado"], 23.5)

    def test_seleccion_tostado_sin_registros_devuelve_ceros(self):
        self.create_order()

        seleccion = get_facturacion_report("2319")["procesos"]["seleccion_tostado"]

        self.assertTrue(seleccion["aplica"])
        self.assertEqual(seleccion["peso_quaker"], 0)
        self.assertEqual(seleccion["peso_grupo1"], 0)
        self.assertEqual(seleccion["peso_grupo2"], 0)
        self.assertEqual(seleccion["peso_grupo3"], 0)
        self.assertEqual(seleccion["total_registrado"], 0)

    def test_pdf_y_html_comparten_consolidacion_de_seleccion_tueste(self):
        orden = self.create_order()
        SeleccionTueste.objects.create(
            orden=orden,
            estado_tareas=self.estado_pendiente,
            peso_quaker=1,
            peso_grupo1=2,
            peso_grupo2=3,
            peso_grupo3=4,
            created_at=timezone.now(),
        )

        html_report = get_facturacion_report("2319")
        pdf_report = get_facturacion_report_by_id(orden.id)

        self.assertEqual(
            html_report["procesos"]["seleccion_tostado"],
            pdf_report["procesos"]["seleccion_tostado"],
        )

    def test_empaque_con_multiples_lineas_y_agrupacion(self):
        orden = self.create_order()
        empaque = Empaque.objects.create(
            orden=orden,
            estado_tareas=self.estado_completada,
            cant_empacada=22,
            total_paquetes=30,
        )
        DetalleEmpaque.objects.create(
            empaque=empaque,
            empaque_cafe=self.empaque_cafe,
            tamano_empaque=self.tamano,
            pedido=20,
            empacado=10,
            suministro=True,
            nivel_molienda=self.molienda,
        )
        DetalleEmpaque.objects.create(
            empaque=empaque,
            empaque_cafe=self.empaque_cafe,
            tamano_empaque=self.tamano,
            pedido=15,
            empacado=7,
            suministro=True,
            nivel_molienda=self.molienda,
        )
        DetalleEmpaque.objects.create(
            empaque=empaque,
            empaque_cafe=self.empaque_cafe_2,
            tamano_empaque=self.tamano_2,
            pedido=5,
            empacado=5,
            suministro=False,
            nivel_molienda=self.molienda,
        )

        rows = get_facturacion_report("2319")["procesos"]["empaque"]["bolsas_empacadas"]

        self.assertEqual(len(rows), 2)
        grouped = {
            (row["empaque_cafe__empaque_cafe"], row["tamano_empaque__tamano_empaque"], row["suministro"]): row["cantidad"]
            for row in rows
        }
        self.assertEqual(grouped[("Bolsa Tricapa Blanca", "500 gr", True)], 17)
        self.assertEqual(grouped[("Bolsa Granel Plastica", "1000 gr", False)], 5)
        self.assertEqual(get_facturacion_report("2319")["procesos"]["empaque"]["cantidad_bolsas_empacadas"], 22)
        self.assertEqual(get_facturacion_report("2319")["procesos"]["empaque"]["total_paquetes"], 30)

    def test_bolsas_empacadas_no_mezcla_lineas_con_suministro_distinto(self):
        orden = self.create_order()
        empaque = Empaque.objects.create(
            orden=orden,
            estado_tareas=self.estado_completada,
            cant_empacada=8,
            total_paquetes=8,
        )
        DetalleEmpaque.objects.create(
            empaque=empaque,
            empaque_cafe=self.empaque_cafe,
            tamano_empaque=self.tamano,
            empacado=5,
            suministro=True,
            nivel_molienda=self.molienda,
        )
        DetalleEmpaque.objects.create(
            empaque=empaque,
            empaque_cafe=self.empaque_cafe,
            tamano_empaque=self.tamano,
            empacado=3,
            suministro=False,
            nivel_molienda=self.molienda,
        )

        rows = get_facturacion_report("2319")["procesos"]["empaque"]["bolsas_empacadas"]

        self.assertEqual(len(rows), 2)
        grouped = {
            (row["empaque_cafe__empaque_cafe"], row["tamano_empaque__tamano_empaque"], row["suministro"]): row["cantidad"]
            for row in rows
        }
        self.assertEqual(grouped[("Bolsa Tricapa Blanca", "500 gr", True)], 5)
        self.assertEqual(grouped[("Bolsa Tricapa Blanca", "500 gr", False)], 3)

    def test_empaque_pendiente_con_detalle_se_muestra_en_facturacion(self):
        orden = self.create_order(orden="4256")
        empaque = Empaque.objects.create(
            orden=orden,
            estado_tareas=self.estado_pendiente,
            cant_empacada=5,
            total_paquetes=7,
        )
        DetalleEmpaque.objects.create(
            empaque=empaque,
            empaque_cafe=self.empaque_cafe,
            tamano_empaque=self.tamano,
            pedido=4,
            empacado=5,
            suministro=True,
            nivel_molienda=self.molienda,
        )

        empaque_section = get_facturacion_report("4256")["procesos"]["empaque"]

        self.assertTrue(empaque_section["bolsas_empacadas"])
        self.assertEqual(empaque_section["cantidad_bolsas_empacadas"], 5)
        self.assertEqual(empaque_section["total_paquetes"], 7)
        self.assertEqual(empaque_section["bolsas_empacadas"][0]["cantidad"], 5)
        self.assertTrue(empaque_section["bolsas_empacadas"][0]["suministro"])

    def test_pdf_usa_mismo_contexto_consolidado_de_la_orden_consultada(self):
        orden = self.create_order(orden="4256")
        empaque = Empaque.objects.create(
            orden=orden,
            estado_tareas=self.estado_pendiente,
            cant_empacada=5,
            total_paquetes=22,
        )
        DetalleEmpaque.objects.create(
            empaque=empaque,
            empaque_cafe=self.empaque_cafe,
            tamano_empaque=self.tamano,
            pedido=4,
            empacado=5,
            suministro=True,
            nivel_molienda=self.molienda,
        )

        report = get_facturacion_report("4256")
        pdf_bytes = render_facturacion_pdf(report)

        from PyPDF2 import PdfReader

        reader = PdfReader(BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)

        self.assertIn("REPORTE DE FACTURACIÓN", text)
        self.assertIn("4256", text)
        self.assertIn("Cliente Facturacion", text)
        self.assertIn("BOLSAS EMPACADAS", text)
        self.assertIn("Sí", text)
        self.assertIn("Cantidad Bolsas Empacadas", text)
        self.assertIn("22", text)

    def test_empaque_suministrado_por_cliente(self):
        orden = self.create_order(trabajo_empaque=True)
        DetalleEmpaqueOrden.objects.create(
            orden=orden,
            empaque_cafe=self.empaque_cafe,
            tamano_empaque=self.tamano,
            cantidad=25,
        )

        empaque = get_facturacion_report("2319")["procesos"]["empaque"]

        self.assertTrue(empaque["suministro_cliente"])
        self.assertEqual(empaque["empaques_suministrados"][0]["cantidad"], 25)

    def test_orden_sin_empaque_suministrado(self):
        self.create_order(trabajo_empaque=False)

        empaque = get_facturacion_report("2319")["procesos"]["empaque"]

        self.assertFalse(empaque["suministro_cliente"])
        self.assertEqual(empaque["empaques_suministrados"], [])

    def test_etiquetas_cliente_cuando_no_requiere_invima(self):
        orden = self.create_order(etiqueta_invima=False)
        Empaque.objects.create(
            orden=orden,
            estado_tareas=self.estado_completada,
            lleva_etiquetas=True,
            cant_etiquetas=12,
        )

        etiquetas = get_facturacion_report("2319")["etiquetas"]

        self.assertEqual(etiquetas["cliente"], 12)
        self.assertEqual(etiquetas["invima"], 0)
        self.assertEqual(etiquetas["total"], 12)

    def test_etiquetas_invima_cuando_requiere_invima(self):
        orden = self.create_order(etiqueta_invima=True)
        Empaque.objects.create(
            orden=orden,
            estado_tareas=self.estado_completada,
            lleva_etiquetas=True,
            cant_etiquetas=8,
        )

        etiquetas = get_facturacion_report("2319")["etiquetas"]

        self.assertEqual(etiquetas["cliente"], 0)
        self.assertEqual(etiquetas["invima"], 8)
        self.assertEqual(etiquetas["total"], 8)

    def test_etiquetas_no_lleva_etiquetas_devuelve_cero(self):
        orden = self.create_order(etiqueta_invima=True)
        Empaque.objects.create(
            orden=orden,
            estado_tareas=self.estado_completada,
            lleva_etiquetas=False,
            cant_etiquetas=99,
        )

        etiquetas = get_facturacion_report("2319")["etiquetas"]

        self.assertEqual(etiquetas["cliente"], 0)
        self.assertEqual(etiquetas["invima"], 0)
        self.assertEqual(etiquetas["total"], 0)

    def test_procesos_configurados_como_no_no_suman_valores(self):
        orden = self.create_order(trilla=False, tueste_flag=False, empaque_flag=False)
        OrdenTrilla.objects.create(
            orden=orden,
            cliente=self.cliente,
            estado_tareas=self.estado_completada,
            peso_cafe_bruto=100,
            peso_cafe_verde=80,
            created_at=timezone.now(),
        )

        report = get_facturacion_report("2319")

        self.assertFalse(report["procesos"]["trilla"]["aplica"])
        self.assertFalse(report["procesos"]["tueste"]["aplica"])
        self.assertFalse(report["procesos"]["empaque"]["aplica"])

    def test_usuario_no_autenticado_es_redirigido(self):
        response = self.client.get(reverse("reportes_facturacion"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_usuario_no_autenticado_no_descarga_pdf(self):
        orden = self.create_order()

        response = self.client.get(reverse("reportes_facturacion_pdf", args=[orden.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_consulta_no_modifica_datos_operativos(self):
        orden = self.create_order()
        OrdenTrilla.objects.create(
            orden=orden,
            cliente=self.cliente,
            estado_tareas=self.estado_completada,
            peso_cafe_bruto=100,
            peso_cafe_verde=80,
            created_at=timezone.now(),
        )
        before = {
            "ordenes": Orden.objects.count(),
            "trillas": OrdenTrilla.objects.count(),
            "tuestes": Tueste.objects.count(),
            "empaques": Empaque.objects.count(),
        }

        get_facturacion_report("2319")

        after = {
            "ordenes": Orden.objects.count(),
            "trillas": OrdenTrilla.objects.count(),
            "tuestes": Tueste.objects.count(),
            "empaques": Empaque.objects.count(),
        }
        self.assertEqual(after, before)

    def test_vista_consulta_orden_existente(self):
        self.create_order()
        self.client.force_login(self.user)

        response = self.client.get(reverse("reportes_facturacion"), {"orden": "2319"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reporte de Facturación")
        self.assertContains(response, "2319")
        self.assertContains(response, "EXPORTAR PDF")

    def test_pdf_devuelve_200_y_application_pdf(self):
        orden = self.create_order()
        self.client.force_login(self.user)

        response = self.client.get(reverse("reportes_facturacion_pdf", args=[orden.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_pdf_orden_inexistente_devuelve_404(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("reportes_facturacion_pdf", args=[999999]))

        self.assertEqual(response.status_code, 404)
