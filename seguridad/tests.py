from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from .helpers import tiene_permiso_accion


class PermisoAccionTests(SimpleTestCase):
    def test_programador_respeta_permiso_django_asignado_en_jazzmin(self):
        user = Mock(is_authenticated=True, is_superuser=False)
        user.has_perm.return_value = True

        permitido = tiene_permiso_accion(
            user,
            django_perm='ordenes_seleccion_verde.change_ordenseleccionverde',
            codigo='editar_orden_seleccion_verde',
        )

        self.assertTrue(permitido)
        user.has_perm.assert_called_once_with(
            'ordenes_seleccion_verde.change_ordenseleccionverde'
        )

    @patch('seguridad.helpers.tiene_permiso', return_value=True)
    def test_conserva_compatibilidad_con_permiso_personalizado(self, permiso_personalizado):
        user = Mock(is_authenticated=True, is_superuser=False)
        user.has_perm.return_value = False

        permitido = tiene_permiso_accion(
            user,
            django_perm='ordenes_seleccion_verde.change_ordenseleccionverde',
            codigo='editar_orden_seleccion_verde',
        )

        self.assertTrue(permitido)
        permiso_personalizado.assert_called_once_with(user, 'editar_orden_seleccion_verde')
