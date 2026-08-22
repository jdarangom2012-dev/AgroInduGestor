from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden

from .helpers import tiene_permiso_accion


def permiso_accion_requerido(django_perm: str | None = None, codigo: str | None = None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if tiene_permiso_accion(request.user, django_perm=django_perm, codigo=codigo):
                return view_func(request, *args, **kwargs)

            if request.headers.get('HX-Request') or request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                return HttpResponseForbidden('No tienes permiso para realizar esta acción.')

            raise PermissionDenied

        return _wrapped

    return decorator