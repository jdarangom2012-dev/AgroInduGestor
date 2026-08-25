from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from seguridad.decorators import permiso_accion_requerido

from .forms import VariendadInvenCafeForm
from .models import VariendadInvenCafe


@permiso_accion_requerido('variendad_inven_cafe.view_variendadinvencafe', 'ver_variendad_inven_cafe')
def listar_variedad_inven_cafe(request):
    qs = VariendadInvenCafe.objects.all()
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(variedad_inven_cafe__icontains=search))
    qs = qs.order_by('variedad_inven_cafe', 'id')

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
        return render(request, 'variendad_inven_cafe/_modal_listar_VariedadInvenCafe.html', ctx)
    return render(request, 'variendad_inven_cafe/listar_VariedadInvenCafe.html', ctx)


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('variendad_inven_cafe.add_variendadinvencafe', 'crear_variendad_inven_cafe')
def add_variedad_inven_cafe(request):
    if request.method == 'POST':
        form = VariendadInvenCafeForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                    return listar_variedad_inven_cafe(request)
                return redirect('variedad_inven_cafe_listar')
    else:
        form = VariendadInvenCafeForm()
    if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
        return render(request, 'variendad_inven_cafe/add_VariedadInvenCafe.html', {'form': form})
    return render(request, 'variendad_inven_cafe/listar_VariedadInvenCafe.html', {})


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('variendad_inven_cafe.change_variendadinvencafe', 'editar_variendad_inven_cafe')
def edit_variedad_inven_cafe(request, pk):
    obj = get_object_or_404(VariendadInvenCafe, pk=pk)
    if request.method == 'POST':
        form = VariendadInvenCafeForm(request.POST, instance=obj)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment'):
                    return listar_variedad_inven_cafe(request)
                return redirect('variedad_inven_cafe_listar')
    else:
        form = VariendadInvenCafeForm(instance=obj)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'variendad_inven_cafe/detail_VariedadInvenCafe.html', {'form': form, 'obj': obj})
    return render(request, 'variendad_inven_cafe/listar_VariedadInvenCafe.html', {})


@permiso_accion_requerido('variendad_inven_cafe.delete_variendadinvencafe', 'eliminar_variendad_inven_cafe')
def delete_variedad_inven_cafe(request, pk):
    obj = get_object_or_404(VariendadInvenCafe, pk=pk)
    if request.method == 'POST':
        obj.delete()
        if request.headers.get('X-Fragment'):
            return listar_variedad_inven_cafe(request)
        return redirect('variedad_inven_cafe_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'variendad_inven_cafe/confirm_delete_VariedadInvenCafe.html', {'obj': obj})
    return render(request, 'variendad_inven_cafe/listar_VariedadInvenCafe.html', {})
