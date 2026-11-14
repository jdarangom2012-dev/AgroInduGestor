from django.db import models


class Reporte(models.Model):
    """Modelo lógico usado únicamente para administrar el acceso a Reportes."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("view_reportes", "Puede ver y exportar reportes"),
        )
        verbose_name = "Acceso a reportes"
        verbose_name_plural = "Acceso a reportes"
