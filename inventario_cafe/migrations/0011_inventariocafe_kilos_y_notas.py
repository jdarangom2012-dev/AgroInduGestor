from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('inventario_cafe', '0010_inventariocafe_cantidad_existente'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventariocafe',
            name='kilos_ingresar',
            field=models.FloatField(blank=True, db_column='KilosIngresar', null=True),
        ),
        migrations.AddField(
            model_name='inventariocafe',
            name='kilos_sacar',
            field=models.FloatField(blank=True, db_column='KilosSacar', null=True),
        ),
        migrations.AddField(
            model_name='inventariocafe',
            name='notas',
            field=models.TextField(blank=True, db_column='Notas', null=True),
        ),
    ]
