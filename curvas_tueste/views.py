from django.shortcuts import render, get_object_or_404, redirect
from seguridad.decorators import permiso_accion_requerido
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django import forms
from django.db.models import Avg, Count, Max, Min, OuterRef, Subquery

from .models import ConsumoTuestePLC, CurvaTueste


class CurvaTuesteForm(forms.ModelForm):
    class Meta:
        model = CurvaTueste
        # fecha_ingreso es automática (no se muestra ni se edita)
        fields = ['temp_set_point', 'temp_tost', 'porcentaje_aire', 'porcentaje_gas']
        widgets = {
            'temp_set_point': forms.NumberInput(attrs={'class': 'w-full input', 'step': '0.1'}),
            'temp_tost': forms.NumberInput(attrs={'class': 'w-full input', 'step': '0.1'}),
            'porcentaje_aire': forms.NumberInput(attrs={'class': 'w-full input', 'step': '0.1', 'min': '0', 'max': '100'}),
            'porcentaje_gas': forms.NumberInput(attrs={'class': 'w-full input', 'step': '0.1', 'min': '0', 'max': '100'}),
        }


@permiso_accion_requerido('curvas_tueste.view_curvatueste', 'ver_curvas_tueste')
def listar_curvas_tueste(request):
    numero_orden = request.GET.get('orden', '').strip()
    bache = request.GET.get('bache', '').strip()
    cliente = request.GET.get('cliente', '').strip()
    consultado = request.GET.get('consultar') == '1'

    if consultado:
        cliente_plc = (
            ConsumoTuestePLC.objects
            .filter(numero_orden=OuterRef('numero_orden'), bache=OuterRef('bache'))
            .order_by('-id')
            .values('cliente')[:1]
        )
        qs = (
            CurvaTueste.objects
            .values('numero_orden', 'bache')
            .annotate(
                fecha_inicio=Min('fecha_ingreso'),
                fecha_fin=Max('fecha_ingreso'),
                lecturas=Count('id'),
                temp_set_promedio=Avg('temp_set_point'),
                temp_real_maxima=Max('temp_tost'),
                aire_promedio=Avg('porcentaje_aire'),
                gas_promedio=Avg('porcentaje_gas'),
                cliente=Subquery(cliente_plc),
            )
            .order_by('-fecha_fin')
        )
        if numero_orden.isdigit():
            qs = qs.filter(numero_orden=int(numero_orden))
        if bache.isdigit():
            qs = qs.filter(bache=int(bache))
        if cliente:
            qs = qs.filter(cliente__icontains=cliente)
    else:
        qs = []

    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    ctx = {
        'curvas': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'page_range': paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1),
        'numero_orden': numero_orden,
        'bache': bache,
        'cliente': cliente,
        'consultado': consultado,
    }
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'curvas_tueste/_modal_listar_CurvasTueste.html', ctx)
    return render(request, 'curvas_tueste/listar_CurvasTueste.html', ctx)


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('curvas_tueste.add_curvatueste', 'crear_curvas_tueste')
def add_curva_tueste(request):
    return redirect('curvas_tueste_listar')


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('curvas_tueste.change_curvatueste', 'editar_curvas_tueste')
def edit_curva_tueste(request, pk):
    return redirect('curvas_tueste_listar')


@permiso_accion_requerido('curvas_tueste.delete_curvatueste', 'eliminar_curvas_tueste')
def delete_curva_tueste(request, pk):
    return redirect('curvas_tueste_listar')
