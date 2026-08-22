from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone

from seguridad.helpers import tiene_permiso_accion

from .models import OrdenSeleccionVerde
from .forms import OrdenSeleccionVerdeForm
from ordenes.forms import enforce_parent_order_not_completed
from ordenes.models import Orden


def permiso_o_codigo_required(django_perm: str, codigo: str):
    """Permite acceso si el usuario tiene el permiso Django o el permiso por rol (RolPermiso).

    Mantiene compatibilidad con `permission_required(..., raise_exception=True)` sin cambiar rutas ni lógica.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            if tiene_permiso_accion(user, django_perm=django_perm, codigo=codigo):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return _wrapped

    return decorator


def _build_orden_seleccion_verde_defaults(orden):
    cliente = getattr(orden, 'cliente', None)
    return {
        'cliente_id': getattr(cliente, 'id', None),
        'cliente_label': str(cliente) if cliente is not None else '',
    }


@require_http_methods(["GET"])
@permiso_o_codigo_required(
    'ordenes_seleccion_verde.add_ordenseleccionverde',
    'crear_orden_seleccion_verde',
)
def orden_seleccion_verde_defaults(request):
    orden_id = request.GET.get('orden_id')
    if not orden_id:
        return JsonResponse(_build_orden_seleccion_verde_defaults(Orden()))

    try:
        orden = Orden.objects.select_related('cliente').get(pk=orden_id, selec_cafe_verde=True)
    except (TypeError, ValueError, Orden.DoesNotExist):
        return JsonResponse({'detail': 'Orden no encontrada.'}, status=404)

    return JsonResponse(_build_orden_seleccion_verde_defaults(orden))


@permiso_o_codigo_required(
    'ordenes_seleccion_verde.view_ordenseleccionverde',
    'ver_ordenes_seleccion_verde',
)
def listar_ordenes_seleccion_verde(request):
    is_fragment = request.GET.get('fragment') == '1' or request.headers.get('X-Fragment')
    if not is_fragment:
        # Unificar render: la página completa solo actúa como "wrapper" y abre el modal vía JS.
        return render(request, 'ordenes_seleccion_verde/listar_OrdenesSelecionVerde.html', {})

    qs = (
        OrdenSeleccionVerde.objects
        .select_related('estado_tareas')
        .only(
            'id','estado_tareas',
            'zaranda','peso_aceptado','humedad','densidad',
        )
        .order_by('-fecha_ingreso','-id')
    )
    search = request.GET.get('q', '').strip()
    if search:
        if search.isdigit():
            qs = qs.filter(id=int(search))
        else:
            qs = qs.filter(
                Q(estado_tareas__estado_tareas__icontains=search) |
                Q(grupo1__icontains=search) | Q(grupo2__icontains=search) |
                Q(grupo3__icontains=search) | Q(grupo4__icontains=search) |
                Q(grupo5__icontains=search)
            )

    paginator = Paginator(qs, 7)
    page = request.GET.get('page')
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    ctx = {
        'items': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'search': search,
    }
    return render(request, 'ordenes_seleccion_verde/_modal_listar_OrdenesSelecionVerde.html', ctx)


@require_http_methods(["GET","POST"])
@permiso_o_codigo_required(
    'ordenes_seleccion_verde.add_ordenseleccionverde',
    'crear_orden_seleccion_verde',
)
def add_orden_seleccion_verde(request):
    if request.method == 'POST':
        form = OrdenSeleccionVerdeForm(request.POST, user=request.user)
        if form.is_valid():
            if not enforce_parent_order_not_completed(form):
                return render(request, 'ordenes_seleccion_verde/add_OrdenesSelecionVerde.html', {'form': form})
            obj = form.save(commit=False)
            if not obj.fecha_ingreso:
                obj.fecha_ingreso = timezone.now()
            obj.created_at = timezone.now()
            obj.updated_at = timezone.now()
            obj.save()
            if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                return listar_ordenes_seleccion_verde(request)
            return redirect('ordenes_seleccion_verde_listar')
    else:
        form = OrdenSeleccionVerdeForm(user=request.user)
    if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
        return render(request, 'ordenes_seleccion_verde/add_OrdenesSelecionVerde.html', {'form': form})
    return render(request, 'ordenes_seleccion_verde/listar_OrdenesSelecionVerde.html', {})


@require_http_methods(["GET","POST"])
@permiso_o_codigo_required(
    'ordenes_seleccion_verde.change_ordenseleccionverde',
    'editar_orden_seleccion_verde',
)
def edit_orden_seleccion_verde(request, pk):
    obj = get_object_or_404(OrdenSeleccionVerde, pk=pk)
    if request.method == 'POST':
        form = OrdenSeleccionVerdeForm(request.POST, instance=obj, user=request.user)
        if form.is_valid():
            if not enforce_parent_order_not_completed(form):
                return render(request, 'ordenes_seleccion_verde/detail_OrdenesSelecionVerde.html', {'form': form, 'obj': obj})
            inst = form.save(commit=False)
            inst.updated_at = timezone.now()
            inst.save()
            if request.headers.get('X-Fragment'):
                return listar_ordenes_seleccion_verde(request)
            return redirect('ordenes_seleccion_verde_listar')
    else:
        form = OrdenSeleccionVerdeForm(instance=obj, user=request.user)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'ordenes_seleccion_verde/detail_OrdenesSelecionVerde.html', {'form': form, 'obj': obj})
    return render(request, 'ordenes_seleccion_verde/listar_OrdenesSelecionVerde.html', {})


@permiso_o_codigo_required(
    'ordenes_seleccion_verde.delete_ordenseleccionverde',
    'eliminar_orden_seleccion_verde',
)
def delete_orden_seleccion_verde(request, pk):
    obj = get_object_or_404(OrdenSeleccionVerde, pk=pk)
    if request.method == 'POST':
        obj.delete()
        if request.headers.get('X-Fragment'):
            return listar_ordenes_seleccion_verde(request)
        return redirect('ordenes_seleccion_verde_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'ordenes_seleccion_verde/confirm_delete_OrdenesSelecionVerde.html', {'t': obj})
    return render(request, 'ordenes_seleccion_verde/listar_OrdenesSelecionVerde.html', {})
