from django.db import migrations


def crear_permiso_asistente_ia(apps, schema_editor):
    Permiso = apps.get_model('seguridad', 'Permiso')
    Permiso.objects.update_or_create(
        codigo='ver_asistente_ia',
        defaults={'descripcion': 'Acceder y realizar consultas en el Asistente IA'},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('seguridad', '0011_fix_programador_orden_produccion_permissions'),
    ]

    operations = [
        migrations.RunPython(crear_permiso_asistente_ia, migrations.RunPython.noop),
    ]
