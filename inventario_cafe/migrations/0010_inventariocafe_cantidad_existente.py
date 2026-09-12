from django.db import migrations, models


def copiar_cantidad_existente(apps, schema_editor):
    InventarioCafe = apps.get_model('inventario_cafe', 'InventarioCafe')
    for inventario in InventarioCafe.objects.all().iterator():
        inventario.cantidad_existente = inventario.cantidad or 0
        inventario.save(update_fields=['cantidad_existente'])


class Migration(migrations.Migration):

    dependencies = [
        ('inventario_cafe', '0009_alter_inventariocafe_variendad_inven_cafe'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventariocafe',
            name='cantidad_existente',
            field=models.FloatField(db_column='CantidadExistente', default=0),
        ),
        migrations.RunPython(copiar_cantidad_existente, migrations.RunPython.noop),
    ]
