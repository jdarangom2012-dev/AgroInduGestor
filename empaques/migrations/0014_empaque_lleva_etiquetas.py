from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empaques', '0013_merge_0012_alter_empaque_notas_0012_detalleempaque'),
    ]

    operations = [
        migrations.AddField(
            model_name='empaque',
            name='lleva_etiquetas',
            field=models.BooleanField(db_column='LlevaEtiquetas', default=False),
        ),
    ]
