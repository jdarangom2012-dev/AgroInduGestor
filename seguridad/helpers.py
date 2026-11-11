from __future__ import annotations

import unicodedata

from django.contrib.auth.models import AnonymousUser

from .models import PerfilUsuario, PermisoCampo, RolModulo, RolPermiso


def tiene_permiso(user, codigo: str) -> bool:
    """Retorna True si el usuario tiene el permiso indicado por código según RolPermiso."""
    if not user or isinstance(user, AnonymousUser) or not getattr(user, 'is_authenticated', False):
        return False

    if getattr(user, 'is_superuser', False):
        return True

    try:
        rol = _get_rol_usuario(user)
    except (PerfilUsuario.DoesNotExist, AttributeError, TypeError, ValueError):
        if codigo in {'crear_orden_produccion', 'ver_orden_produccion'}:
            print(f"[PERMISOS DEBUG] user={getattr(user, 'username', None)} codigo={codigo} sin rol/perfil")
        return False

    permisos_usuario = list(
        RolPermiso.objects.filter(rol=rol)
        .select_related('permiso')
        .values_list('permiso__codigo', flat=True)
    )

    if codigo in {'crear_orden_produccion', 'ver_orden_produccion'}:
        print(
            f"[PERMISOS DEBUG] user={getattr(user, 'username', None)} rol={getattr(rol, 'nombre', None)} "
            f"codigo={codigo} permisos={sorted(permisos_usuario)}"
        )

    return codigo in permisos_usuario


def tiene_rol(user, nombre_rol: str) -> bool:
    if getattr(user, 'is_superuser', False):
        return True

    if not _usuario_autenticado(user):
        return False

    try:
        rol = _get_rol_usuario(user)
    except (PerfilUsuario.DoesNotExist, AttributeError, TypeError, ValueError):
        return False

    return normalizar(getattr(rol, 'nombre', '')) == normalizar(nombre_rol)


def es_programador(user) -> bool:
    if getattr(user, 'is_superuser', False):
        return False

    return tiene_rol(user, 'Programador')


def tiene_permiso_accion(user, django_perm: str | None = None, codigo: str | None = None) -> bool:
    if getattr(user, 'is_superuser', False):
        return True

    if not _usuario_autenticado(user):
        return False

    if django_perm and user.has_perm(django_perm):
        return True

    if codigo:
        return tiene_permiso(user, codigo)

    return False


def tiene_modulo(user, nombre_modulo: str) -> bool:
    if getattr(user, 'is_superuser', False):
        return True

    if not _usuario_autenticado(user):
        return False

    try:
        rol = _get_rol_usuario(user)
    except (PerfilUsuario.DoesNotExist, AttributeError, TypeError, ValueError):
        return False

    nombre_modulo = normalizar(nombre_modulo)
    if not nombre_modulo:
        return False

    nombres_modulos = RolModulo.objects.filter(rol=rol).select_related('modulo').values_list('modulo__nombre', flat=True)
    return any(normalizar(nombre_bd) == nombre_modulo for nombre_bd in nombres_modulos)


def puede_ver_campo(user, modelo: str, campo: str) -> bool:
    if getattr(user, 'is_superuser', False):
        return True

    if not _usuario_autenticado(user):
        return False

    try:
        rol = _get_rol_usuario(user)
        permiso = PermisoCampo.objects.get(rol=rol, modelo=modelo, campo=campo)
        return bool(permiso.puede_ver)
    except (PerfilUsuario.DoesNotExist, PermisoCampo.DoesNotExist, AttributeError, TypeError, ValueError):
        return False


def puede_editar_campo(user, modelo: str, campo: str) -> bool:
    if getattr(user, 'is_superuser', False):
        return True

    if not _usuario_autenticado(user):
        return False

    try:
        rol = _get_rol_usuario(user)
        permiso = PermisoCampo.objects.get(rol=rol, modelo=modelo, campo=campo)
        return bool(permiso.puede_editar)
    except (PerfilUsuario.DoesNotExist, PermisoCampo.DoesNotExist, AttributeError, TypeError, ValueError):
        return False


def _usuario_autenticado(user) -> bool:
    return bool(user) and not isinstance(user, AnonymousUser) and bool(getattr(user, 'is_authenticated', False))


def normalizar(texto) -> str:
    texto = str(texto or '').strip().lower()
    if not texto:
        return ''

    texto_normalizado = unicodedata.normalize('NFKD', texto)
    return ''.join(caracter for caracter in texto_normalizado if not unicodedata.combining(caracter))


def _get_rol_usuario(user):
    """Obtiene el rol asociado al usuario.

    Soporta distintos nombres de relación (por ejemplo `user.profile` en este proyecto)
    y cae a consulta por si el related object no está cacheado.
    """
    perfil = getattr(user, 'perfilusuario', None) or getattr(user, 'profile', None)
    rol = getattr(perfil, 'rol', None)
    if rol is not None:
        return rol

    perfil_db = PerfilUsuario.objects.select_related('rol').get(user=user)
    if not perfil_db.rol_id:
        raise AttributeError('Usuario sin rol')
    return perfil_db.rol
