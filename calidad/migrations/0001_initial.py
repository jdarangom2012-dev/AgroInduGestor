import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('clientes', '0001_initial'),
        ('proceso_inven_cafe', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Calidad',
            fields=[
                ('id', models.BigAutoField(db_column='Id', primary_key=True, serialize=False)),
                ('fecha_ingreso', models.DateTimeField(auto_now_add=True, db_column='FechaIngreso')),
                ('fecha_recibido', models.DateField(blank=True, db_column='FechaRecibido', null=True)),
                ('sencilla', models.BooleanField(db_column='Sencilla', default=False)),
                ('q_grader', models.BooleanField(db_column='QGrader', default=False)),
                ('muestra_numero', models.CharField(blank=True, db_column='MuestraNumero', max_length=30)),
                ('orden', models.CharField(db_column='Orden', max_length=50)),
                ('variedad', models.CharField(blank=True, db_column='Variedad', max_length=80)),
                ('origen', models.CharField(blank=True, db_column='Origen', max_length=80)),
                ('altura', models.FloatField(blank=True, db_column='Altura', null=True)),
                ('peso_pergamino', models.FloatField(blank=True, db_column='PesoPergamino', null=True)),
                ('humedad', models.FloatField(blank=True, db_column='Humedad', null=True)),
                ('densidad', models.FloatField(blank=True, db_column='Densidad', null=True)),
                ('peso_verde', models.FloatField(blank=True, db_column='PesoVerde', null=True)),
                ('peso_excelsio', models.FloatField(blank=True, db_column='PesoExcelsio', null=True)),
                ('factor', models.FloatField(blank=True, db_column='Factor', null=True)),
                ('notas', models.TextField(blank=True, db_column='Notas')),
                ('tostion_json', models.TextField(db_column='Tostion', default='[]')),
                ('peso_tostado', models.FloatField(blank=True, db_column='PesoTostado', null=True)),
                ('observaciones', models.TextField(blank=True, db_column='Observaciones')),
                ('cliente', models.ForeignKey(db_column='IdCliente', on_delete=django.db.models.deletion.PROTECT, to='clientes.cliente')),
                ('proceso', models.ForeignKey(db_column='IdProceso', on_delete=django.db.models.deletion.PROTECT, to='proceso_inven_cafe.procesoinvencafe')),
            ],
            options={'db_table': 'tblcalidad', 'ordering': ['-fecha_ingreso', '-id']},
        ),
    ]
