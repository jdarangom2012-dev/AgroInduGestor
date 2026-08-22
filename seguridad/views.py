from functools import wraps

from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from django.core.exceptions import ValidationError

from .forms import ModuloForm, PermisoCampoForm, PermisoForm, RolForm
from .helpers import es_programador, puede_editar_campo, tiene_modulo, tiene_permiso
from .models import Modulo, Permiso, PermisoCampo, Rol, RolModulo, RolPermiso


def _solo_staff(user):
    return bool(user and user.is_authenticated and user.is_staff)


def _puede_ver_seguridad(user):
    if not _solo_staff(user):
        return False

    return bool(
        getattr(user, 'is_superuser', False)
        or tiene_permiso(user, 'configurar_sistema')
        or tiene_modulo(user, 'Seguridad')
    )


def _puede_gestionar_seguridad(user):
    return _solo_staff(user) and not es_programador(user)


def _requiere_acceso_seguridad(predicate):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if predicate(request.user):
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden('No tienes permiso para acceder a esta sección.')
        return wrapped
    return decorator


@login_required
@_requiere_acceso_seguridad(_puede_ver_seguridad)
def roles_listar(request):
    items = Rol.objects.all().order_by('nombre', 'id')
    return render(request, 'seguridad/roles_listar.html', {
        'items': items,
        'puede_gestionar_seguridad': _puede_gestionar_seguridad(request.user),
    })


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def roles_crear(request):
    if request.method == 'POST':
        form = RolForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Rol creado correctamente.')
            return redirect('seguridad_roles_listar')
    else:
        form = RolForm()
    return render(request, 'seguridad/roles_form.html', {'form': form, 'titulo': 'Nuevo Rol'})


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def roles_editar(request, pk: int):
    obj = get_object_or_404(Rol, pk=pk)
    if request.method == 'POST':
        form = RolForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Rol actualizado correctamente.')
            return redirect('seguridad_roles_listar')
    else:
        form = RolForm(instance=obj)
    return render(request, 'seguridad/roles_form.html', {'form': form, 'titulo': 'Editar Rol', 'obj': obj})


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def roles_eliminar(request, pk: int):
    obj = get_object_or_404(Rol, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Rol eliminado.')
        return redirect('seguridad_roles_listar')
    return render(request, 'seguridad/confirm_delete.html', {'obj': obj, 'titulo': 'Eliminar Rol'})


@login_required
@_requiere_acceso_seguridad(_puede_ver_seguridad)
def permisos_listar(request):
    items = Permiso.objects.all().order_by('codigo', 'id')
    return render(request, 'seguridad/permisos_listar.html', {
        'items': items,
        'puede_gestionar_seguridad': _puede_gestionar_seguridad(request.user),
    })


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def permisos_crear(request):
    if request.method == 'POST':
        form = PermisoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Permiso creado correctamente.')
            return redirect('seguridad_permisos_listar')
    else:
        form = PermisoForm()
    return render(request, 'seguridad/permisos_form.html', {'form': form, 'titulo': 'Nuevo Permiso'})


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def permisos_editar(request, pk: int):
    obj = get_object_or_404(Permiso, pk=pk)
    if request.method == 'POST':
        form = PermisoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Permiso actualizado correctamente.')
            return redirect('seguridad_permisos_listar')
    else:
        form = PermisoForm(instance=obj)
    return render(request, 'seguridad/permisos_form.html', {'form': form, 'titulo': 'Editar Permiso', 'obj': obj})


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def permisos_eliminar(request, pk: int):
    obj = get_object_or_404(Permiso, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Permiso eliminado.')
        return redirect('seguridad_permisos_listar')
    return render(request, 'seguridad/confirm_delete.html', {'obj': obj, 'titulo': 'Eliminar Permiso'})


@login_required
@_requiere_acceso_seguridad(_puede_ver_seguridad)
def modulos_listar(request):
    items = Modulo.objects.all().order_by('orden', 'nombre', 'id')
    return render(request, 'seguridad/modulos_listar.html', {
        'items': items,
        'puede_gestionar_seguridad': _puede_gestionar_seguridad(request.user),
    })


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def modulos_crear(request):
    if request.method == 'POST':
        form = ModuloForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Módulo creado correctamente.')
            return redirect('seguridad_modulos_listar')
    else:
        form = ModuloForm()
    return render(request, 'seguridad/modulos_form.html', {'form': form, 'titulo': 'Nuevo Módulo'})


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def modulos_editar(request, pk: int):
    obj = get_object_or_404(Modulo, pk=pk)
    if request.method == 'POST':
        form = ModuloForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Módulo actualizado correctamente.')
            return redirect('seguridad_modulos_listar')
    else:
        form = ModuloForm(instance=obj)
    return render(request, 'seguridad/modulos_form.html', {'form': form, 'titulo': 'Editar Módulo', 'obj': obj})


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def modulos_eliminar(request, pk: int):
    obj = get_object_or_404(Modulo, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Módulo eliminado.')
        return redirect('seguridad_modulos_listar')
    return render(request, 'seguridad/confirm_delete.html', {'obj': obj, 'titulo': 'Eliminar Módulo'})


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def gestionar_permisos(request):
    roles = Rol.objects.all().order_by('nombre', 'id')
    role_id = request.GET.get('rol') or request.POST.get('rol')
    rol_actual = None

    modulos = list(Modulo.objects.all().order_by('orden', 'nombre', 'id'))
    permisos = list(Permiso.objects.all().order_by('codigo', 'id'))

    seleccion_modulos = set()
    seleccion_permisos = set()

    if role_id:
        rol_actual = get_object_or_404(Rol, pk=role_id)
        seleccion_modulos = set(
            RolModulo.objects.filter(rol=rol_actual).values_list('modulo_id', flat=True)
        )
        seleccion_permisos = set(
            RolPermiso.objects.filter(rol=rol_actual).values_list('permiso_id', flat=True)
        )

    if request.method == 'POST' and rol_actual:
        nuevos_modulos = {int(v) for v in request.POST.getlist('modulos') if v.isdigit()}
        nuevos_permisos = {int(v) for v in request.POST.getlist('permisos') if v.isdigit()}

        with transaction.atomic():
            # Compatible con cualquier motor: borrar y recrear asignaciones.
            RolModulo.objects.filter(rol=rol_actual).delete()
            RolPermiso.objects.filter(rol=rol_actual).delete()

            for modulo_id in nuevos_modulos:
                RolModulo.objects.create(rol=rol_actual, modulo_id=modulo_id)

            for permiso_id in nuevos_permisos:
                RolPermiso.objects.create(rol=rol_actual, permiso_id=permiso_id)

        messages.success(request, 'Asignaciones guardadas correctamente.')
        return redirect(f"{request.path}?rol={rol_actual.id}")

    # Agrupar permisos por tipo (prefijo antes del primer underscore)
    permisos_por_tipo = defaultdict(list)
    for p in permisos:
        prefijo = (p.codigo.split('_', 1)[0] if '_' in p.codigo else 'otros').strip() or 'otros'
        permisos_por_tipo[prefijo].append(p)

    ctx = {
        'roles': roles,
        'rol_actual': rol_actual,
        'modulos': modulos,
        'permisos_por_tipo': dict(sorted(permisos_por_tipo.items(), key=lambda kv: kv[0])),
        'seleccion_modulos': seleccion_modulos,
        'seleccion_permisos': seleccion_permisos,
    }
    return render(request, 'seguridad/gestionar_permisos.html', ctx)


def validar_permisos_campo(user, modelo: str, datos_originales: dict, datos_nuevos: dict) -> None:
    """Valida que no se estén editando campos no permitidos.

    Integración progresiva: esta función se puede llamar desde cualquier vista
    antes de guardar (sin hardcodear formularios específicos).
    """
    errores = {}
    for campo, nuevo_valor in (datos_nuevos or {}).items():
        if not puede_editar_campo(user, modelo, campo):
            original = (datos_originales or {}).get(campo)
            if nuevo_valor != original:
                errores[campo] = 'No tienes permiso para editar este campo.'
    if errores:
        raise ValidationError(errores)


@login_required
@_requiere_acceso_seguridad(_puede_ver_seguridad)
def permisos_campo_listar(request):
    items = PermisoCampo.objects.select_related('rol').all().order_by('modelo', 'campo', 'rol__nombre', 'id')
    return render(request, 'seguridad/permisos_campo_listar.html', {
        'items': items,
        'puede_gestionar_seguridad': _puede_gestionar_seguridad(request.user),
    })


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def permisos_campo_crear(request):
    if request.method == 'POST':
        form = PermisoCampoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Permiso de campo creado correctamente.')
            return redirect('seguridad_permisos_campo_listar')
    else:
        form = PermisoCampoForm()
    return render(request, 'seguridad/permisos_campo_form.html', {'form': form, 'titulo': 'Nuevo Permiso de Campo'})


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def permisos_campo_editar(request, pk: int):
    obj = get_object_or_404(PermisoCampo, pk=pk)
    if request.method == 'POST':
        form = PermisoCampoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Permiso de campo actualizado correctamente.')
            return redirect('seguridad_permisos_campo_listar')
    else:
        form = PermisoCampoForm(instance=obj)
    return render(
        request,
        'seguridad/permisos_campo_form.html',
        {'form': form, 'titulo': 'Editar Permiso de Campo', 'obj': obj},
    )


@login_required
@_requiere_acceso_seguridad(_puede_gestionar_seguridad)
@require_http_methods(["GET", "POST"])
def permisos_campo_eliminar(request, pk: int):
    obj = get_object_or_404(PermisoCampo, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Permiso de campo eliminado.')
        return redirect('seguridad_permisos_campo_listar')
    return render(request, 'seguridad/confirm_delete.html', {'obj': obj, 'titulo': 'Eliminar Permiso de Campo'})
