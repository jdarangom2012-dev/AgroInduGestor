from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from seguridad.decorators import permiso_accion_requerido
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from .models import OrigenCafe
from .forms import OrigenCafeForm


@permiso_accion_requerido('origen_cafe.view_origencafe', 'ver_origenes')
def listar_origen_cafe(request):
    qs = OrigenCafe.objects.all()
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(origen__icontains=search))
    qs = qs.order_by('origen', 'id')

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
        return render(request, 'origen_cafe/_modal_listar_OrigenCafe.html', ctx)
    return render(request, 'origen_cafe/listar_OrigenCafe.html', ctx)


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('origen_cafe.add_origencafe', 'crear_origenes')
def add_origen_cafe(request):
    if request.method == 'POST':
        form = OrigenCafeForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                    return listar_origen_cafe(request)
                return redirect('origen_cafe_listar')
    else:
        form = OrigenCafeForm()
    if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
        return render(request, 'origen_cafe/add_OrigenCafe.html', {'form': form})
    return render(request, 'origen_cafe/listar_OrigenCafe.html', {})


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('origen_cafe.change_origencafe', 'editar_origenes')
def edit_origen_cafe(request, pk):
    obj = get_object_or_404(OrigenCafe, pk=pk)
    if request.method == 'POST':
        form = OrigenCafeForm(request.POST, instance=obj)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment'):
                    return listar_origen_cafe(request)
                return redirect('origen_cafe_listar')
    else:
        form = OrigenCafeForm(instance=obj)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'origen_cafe/detail_OrigenCafe.html', {'form': form, 'obj': obj})
    return render(request, 'origen_cafe/listar_OrigenCafe.html', {})


@permiso_accion_requerido('origen_cafe.delete_origencafe', 'eliminar_origenes')
def delete_origen_cafe(request, pk):
    obj = get_object_or_404(OrigenCafe, pk=pk)
    if request.method == 'POST':
        obj.delete()
        if request.headers.get('X-Fragment'):
            return listar_origen_cafe(request)
        return redirect('origen_cafe_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'origen_cafe/confirm_delete_OrigenCafe.html', {'obj': obj})
    return render(request, 'origen_cafe/listar_OrigenCafe.html', {})
