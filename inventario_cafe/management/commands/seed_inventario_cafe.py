import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from inventario_cafe.models import InventarioCafe
from clientes.models import Cliente
from estado_cafe.models import EstadoCafe
from proceso_inven_cafe.models import ProcesoInvenCafe
from variendad_inven_cafe.models import VariendadInvenCafe
from origen_cafe.models import OrigenCafe
from cafe_empaque.models import CafeEmpaque


class Command(BaseCommand):
    help = "Inserta registros de InventarioCafe hasta completar un máximo dado (por defecto 50)."

    def add_arguments(self, parser):
        parser.add_argument('--max', type=int, default=50, help='Máximo total de registros a garantizar')

    def handle(self, *args, **options):
        max_total = max(0, int(options['max']))

        # Garantizar catálogos mínimos para claves foráneas (si no hay, crear algunos básicos)
        if Cliente.objects.count() == 0:
            Cliente.objects.create(nombre='Cliente Demo')
        if EstadoCafe.objects.count() == 0:
            EstadoCafe.objects.create(estado_cafe='Estado Demo')
        if ProcesoInvenCafe.objects.count() == 0:
            ProcesoInvenCafe.objects.create(proceso_inven_cafe='Lavado')
        if VariendadInvenCafe.objects.count() == 0:
            VariendadInvenCafe.objects.create(variedad_inven_cafe='Caturra')
        if OrigenCafe.objects.count() == 0:
            OrigenCafe.objects.create(origen='Origen Demo')
        if CafeEmpaque.objects.count() == 0:
            CafeEmpaque.objects.create(empaque_cafe='Saco 69kg')

        clientes = list(Cliente.objects.all())
        estados = list(EstadoCafe.objects.all())
        procesos = list(ProcesoInvenCafe.objects.all())
        variedades = list(VariendadInvenCafe.objects.all())
        origenes = list(OrigenCafe.objects.all())
        empaques = list(CafeEmpaque.objects.all())

        current = InventarioCafe.objects.count()
        to_create = max_total - current
        if to_create <= 0:
            self.stdout.write(self.style.SUCCESS(f"Ya existen {current} registros, no se crean nuevos (máximo {max_total})."))
            return

        objs = []
        now = timezone.now()
        for i in range(to_create):
            codigo = f"INV-{now.strftime('%Y%m%d')}-{current + i + 1:04d}"
            cantidad = round(random.uniform(5, 100), 2)
            sacos = random.randint(0, 20)
            bolsas = random.randint(0, 100)
            paquetes = random.randint(0, 200)
            fecha = now - timedelta(days=random.randint(0, 90))
            objs.append(InventarioCafe(
                cliente=random.choice(clientes),
                estado_cafe=random.choice(estados),
                proceso_inven_cafe=random.choice(procesos),
                variendad_inven_cafe=random.choice(variedades),
                origen=random.choice(origenes),
                empaquecafe=random.choice(empaques),
                fecha_ingreso=fecha,
                codigo=codigo,
                cantidad=cantidad,
                cantidad_existente=cantidad,
                sacos=sacos,
                cantidad_bolsas_emp=bolsas,
                cantidad_paquetes=paquetes,
                created_at=fecha,
                updated_at=fecha,
            ))

        InventarioCafe.objects.bulk_create(objs, batch_size=100)
        self.stdout.write(self.style.SUCCESS(f"Creados {len(objs)} registros de InventarioCafe (total ahora: {InventarioCafe.objects.count()})."))
