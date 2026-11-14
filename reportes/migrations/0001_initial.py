from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Reporte",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ],
            options={
                "verbose_name": "Acceso a reportes",
                "verbose_name_plural": "Acceso a reportes",
                "permissions": (("view_reportes", "Puede ver y exportar reportes"),),
                "default_permissions": (),
                "managed": False,
            },
        ),
    ]
