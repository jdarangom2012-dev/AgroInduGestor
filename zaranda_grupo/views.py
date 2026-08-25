from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from seguridad.decorators import permiso_accion_requerido
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django import forms

from .models import ZarandaGrupo


class ZarandaGrupoForm(forms.ModelForm):
    class Meta:
        model = ZarandaGrupo
        fields = ['zaranda_grupo']
        widgets = {
            'zaranda_grupo': forms.TextInput(attrs={'class': 'w-full input'}),
        }


@permiso_accion_requerido('zaranda_grupo.view_zarandagrupo', 'ver_zaranda_grupo')
def listar_zaranda_grupo(request):
    qs = ZarandaGrupo.objects.all()
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(zaranda_grupo__icontains=search))
    qs = qs.order_by('zaranda_grupo', 'id')

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
        return render(request, 'zaranda_grupo/_modal_listar_ZarandaGrupo.html', ctx)
    return render(request, 'zaranda_grupo/listar_ZarandaGrupo.html', ctx)


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('zaranda_grupo.add_zarandagrupo', 'crear_zaranda_grupo')
def add_zaranda_grupo(request):
    if request.method == 'POST':
        form = ZarandaGrupoForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                    return listar_zaranda_grupo(request)
                return redirect('zaranda_grupo_listar')
    else:
        form = ZarandaGrupoForm()
    if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
        return render(request, 'zaranda_grupo/add_ZarandaGrupo.html', {'form': form})
    return render(request, 'zaranda_grupo/listar_ZarandaGrupo.html', {})


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('zaranda_grupo.change_zarandagrupo', 'editar_zaranda_grupo')
def edit_zaranda_grupo(request, pk):
    obj = get_object_or_404(ZarandaGrupo, pk=pk)
    if request.method == 'POST':
        form = ZarandaGrupoForm(request.POST, instance=obj)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment'):
                    return listar_zaranda_grupo(request)
                return redirect('zaranda_grupo_listar')
    else:
        form = ZarandaGrupoForm(instance=obj)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'zaranda_grupo/detail_ZarandaGrupo.html', {'form': form, 'obj': obj})
    return render(request, 'zaranda_grupo/listar_ZarandaGrupo.html', {})


@permiso_accion_requerido('zaranda_grupo.delete_zarandagrupo', 'eliminar_zaranda_grupo')
def delete_zaranda_grupo(request, pk):
    obj = get_object_or_404(ZarandaGrupo, pk=pk)
    if request.method == 'POST':
        obj.delete()
        if request.headers.get('X-Fragment'):
            return listar_zaranda_grupo(request)
        return redirect('zaranda_grupo_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'zaranda_grupo/confirm_delete_ZarandaGrupo.html', {'obj': obj})
    return render(request, 'zaranda_grupo/listar_ZarandaGrupo.html', {})
