from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from seguridad.decorators import permiso_accion_requerido
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Material
from .forms import MaterialForm


@permiso_accion_requerido('materiales.view_material', 'ver_materiales')
def listar_materiales(request):
    qs = Material.objects.select_related('cliente')
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(codigo_material__icontains=search) |
            Q(descripcion__icontains=search)
        )
    qs = qs.order_by('descripcion','id')

    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    try:
        materiales_page = paginator.page(page)
    except PageNotAnInteger:
        materiales_page = paginator.page(1)
    except EmptyPage:
        materiales_page = paginator.page(paginator.num_pages)

    ctx = {
        'materiales': materiales_page,
        'page_obj': materiales_page,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'search': search,
    }
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'materiales/_modal_listar_materiales.html', ctx)
    return render(request, 'materiales/listar_Materiales.html', ctx)


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('materiales.add_material', 'crear_materiales')
def add_material(request):
    if request.method == 'POST':
        form = MaterialForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            from django.utils import timezone
            obj.created_at = timezone.now()
            obj.updated_at = timezone.now()
            if not obj.fecha_ingreso:
                obj.fecha_ingreso = timezone.now()
            try:
                obj.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                    return listar_materiales(request)
                return redirect('materiales_listar')
    else:
        form = MaterialForm()
    if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
        return render(request, 'materiales/add_Materiales.html', {'form': form})
    return render(request, 'materiales/listar_Materiales.html', {})


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('materiales.change_material', 'editar_materiales')
def edit_material(request, pk):
    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            obj = form.save(commit=False)
            from django.utils import timezone
            obj.updated_at = timezone.now()
            try:
                obj.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment'):
                    return listar_materiales(request)
                return redirect('materiales_listar')
    else:
        form = MaterialForm(instance=material)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'materiales/detail_Materiales.html', {'form': form, 'material': material})
    return render(request, 'materiales/listar_Materiales.html', {})


@permiso_accion_requerido('materiales.delete_material', 'eliminar_materiales')
def delete_material(request, pk):
    m = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        m.delete()
        if request.headers.get('X-Fragment'):
            return listar_materiales(request)
        return redirect('materiales_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'materiales/confirm_delete_material.html', {'m': m})
    return render(request, 'materiales/listar_Materiales.html', {})
