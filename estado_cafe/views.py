from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from seguridad.decorators import permiso_accion_requerido
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from .models import EstadoCafe
from .forms import EstadoForm


@permiso_accion_requerido('estado_cafe.view_estadocafe', 'ver_estados')
def listar_estado(request):
    qs = EstadoCafe.objects.all()
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(estado_cafe__icontains=search))
    qs = qs.order_by('estado_cafe', 'id')

    paginator = Paginator(qs, 10)
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
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'estado/_modal_listar_Estado.html', ctx)
    return render(request, 'estado/listar_Estado.html', ctx)


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('estado_cafe.add_estadocafe', 'crear_estados')
def add_estado(request):
    if request.method == 'POST':
        form = EstadoForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                    return listar_estado(request)
                return redirect('estado_listar')
    else:
        form = EstadoForm()
    if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
        return render(request, 'estado/add_Estado.html', {'form': form})
    return render(request, 'estado/listar_Estado.html', {})


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('estado_cafe.change_estadocafe', 'editar_estados')
def edit_estado(request, pk):
    obj = get_object_or_404(EstadoCafe, pk=pk)
    if request.method == 'POST':
        form = EstadoForm(request.POST, instance=obj)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment'):
                    return listar_estado(request)
                return redirect('estado_listar')
    else:
        form = EstadoForm(instance=obj)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'estado/detail_Estado.html', {'form': form, 'obj': obj})
    return render(request, 'estado/listar_Estado.html', {})


@permiso_accion_requerido('estado_cafe.delete_estadocafe', 'eliminar_estados')
def delete_estado(request, pk):
    obj = get_object_or_404(EstadoCafe, pk=pk)
    if request.method == 'POST':
        obj.delete()
        if request.headers.get('X-Fragment'):
            return listar_estado(request)
        return redirect('estado_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'estado/confirm_delete_Estado.html', {'obj': obj})
    return render(request, 'estado/listar_Estado.html', {})
