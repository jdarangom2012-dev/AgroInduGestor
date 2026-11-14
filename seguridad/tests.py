from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from .helpers import tiene_permiso_accion, tiene_permiso_grupo


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
    def test_permiso_django_es_la_fuente_para_acciones_crud(self, permiso_personalizado):
        user = Mock(is_authenticated=True, is_superuser=False)
        user.has_perm.return_value = False

        permitido = tiene_permiso_accion(
            user,
            django_perm='ordenes_seleccion_verde.change_ordenseleccionverde',
            codigo='editar_orden_seleccion_verde',
        )

        self.assertFalse(permitido)
        permiso_personalizado.assert_not_called()

    @patch('seguridad.helpers.tiene_permiso', return_value=True)
    def test_funcion_sin_permiso_django_conserva_permiso_especial(self, permiso_personalizado):
        user = Mock(is_authenticated=True, is_superuser=False)

        permitido = tiene_permiso_accion(user, codigo='ver_asistente_ia')

        self.assertTrue(permitido)
        permiso_personalizado.assert_called_once_with(user, 'ver_asistente_ia')


class PermisoGrupoTests(SimpleTestCase):
    def test_acepta_permiso_asignado_al_grupo(self):
        user = Mock(is_authenticated=True, is_superuser=False)
        user.groups.filter.return_value.exists.return_value = True

        self.assertTrue(tiene_permiso_grupo(
            user,
            'ordenes_seleccion_verde.change_ordenseleccionverde',
        ))
        user.groups.filter.assert_called_once_with(
            permissions__content_type__app_label='ordenes_seleccion_verde',
            permissions__codename='change_ordenseleccionverde',
        )

    def test_ignora_permiso_directo_si_el_grupo_no_lo_tiene(self):
        user = Mock(is_authenticated=True, is_superuser=False)
        user.has_perm.return_value = True
        user.groups.filter.return_value.exists.return_value = False

        self.assertFalse(tiene_permiso_grupo(
            user,
            'ordenes_seleccion_verde.delete_ordenseleccionverde',
        ))
        user.has_perm.assert_not_called()
