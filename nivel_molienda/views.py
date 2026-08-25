from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from seguridad.decorators import permiso_accion_requerido
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from .models import NivelMolienda
from .forms import NivelMoliendaForm


@permiso_accion_requerido('nivel_molienda.view_nivelmolienda', 'ver_nivel_molienda')
def listar_niveles_molienda(request):
    qs = NivelMolienda.objects.all()
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(nivel_molienda__icontains=search))
    qs = qs.order_by('nivel_molienda', 'id')

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
        return render(request, 'nivel_molienda/_modal_listar_NivelesMolienda.html', ctx)
    return render(request, 'nivel_molienda/listar_NivelesMolienda.html', ctx)


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('nivel_molienda.add_nivelmolienda', 'crear_nivel_molienda')
def add_nivel_molienda(request):
    if request.method == 'POST':
        form = NivelMoliendaForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                    return listar_niveles_molienda(request)
                return redirect('nivel_molienda_listar')
    else:
        form = NivelMoliendaForm()
    if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
        return render(request, 'nivel_molienda/add_NivelesMolienda.html', {'form': form})
    return render(request, 'nivel_molienda/listar_NivelesMolienda.html', {})


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('nivel_molienda.change_nivelmolienda', 'editar_nivel_molienda')
def edit_nivel_molienda(request, pk):
    obj = get_object_or_404(NivelMolienda, pk=pk)
    if request.method == 'POST':
        form = NivelMoliendaForm(request.POST, instance=obj)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment'):
                    return listar_niveles_molienda(request)
                return redirect('nivel_molienda_listar')
    else:
        form = NivelMoliendaForm(instance=obj)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'nivel_molienda/detail_NivelesMolienda.html', {'form': form, 'obj': obj})
    return render(request, 'nivel_molienda/listar_NivelesMolienda.html', {})


@permiso_accion_requerido('nivel_molienda.delete_nivelmolienda', 'eliminar_nivel_molienda')
def delete_nivel_molienda(request, pk):
    obj = get_object_or_404(NivelMolienda, pk=pk)
    if request.method == 'POST':
        obj.delete()
        if request.headers.get('X-Fragment'):
            return listar_niveles_molienda(request)
        return redirect('nivel_molienda_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'nivel_molienda/confirm_delete_NivelesMolienda.html', {'obj': obj})
    return render(request, 'nivel_molienda/listar_NivelesMolienda.html', {})
