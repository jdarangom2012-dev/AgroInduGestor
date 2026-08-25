from django.shortcuts import render, get_object_or_404, redirect
from seguridad.decorators import permiso_accion_requerido
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django import forms
from django.utils import timezone
from django.urls import reverse
from urllib.parse import urlencode

from .models import InventarioCafe
from origen_cafe.models import OrigenCafe
from proceso_inven_cafe.models import ProcesoInvenCafe
from variedad_cafe.models import VariedadCafe
from clientes.models import Cliente
from estado_cafe.models import EstadoCafe
from cafe_empaque.models import CafeEmpaque


class InventarioCafeForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(queryset=Cliente.objects.all().order_by('nombre'), required=False, widget=forms.Select(attrs={'class': 'w-full select'}))
    estado_cafe = forms.ModelChoiceField(queryset=EstadoCafe.objects.all().order_by('estado_cafe'), required=False, widget=forms.Select(attrs={'class': 'w-full select'}))
    empaquecafe = forms.ModelChoiceField(queryset=CafeEmpaque.objects.all().order_by('empaque_cafe'), required=False, widget=forms.Select(attrs={'class': 'w-full select'}))
    origen = forms.ModelChoiceField(queryset=OrigenCafe.objects.all().order_by('origen'), required=False, widget=forms.Select(attrs={'class': 'w-full select'}))
    proceso_inven_cafe = forms.ModelChoiceField(queryset=ProcesoInvenCafe.objects.all().order_by('proceso_inven_cafe'), required=False, widget=forms.Select(attrs={'class': 'w-full select'}))
    variendad_inven_cafe = forms.ModelChoiceField(queryset=VariedadCafe.objects.all().order_by('variedad_cafe'), required=False, widget=forms.Select(attrs={'class': 'w-full select'}))

    class Meta:
        model = InventarioCafe
        fields = ['cliente', 'estado_cafe', 'origen', 'proceso_inven_cafe', 'variendad_inven_cafe', 'empaquecafe', 'codigo', 'descripcion', 'cantidad', 'sacos', 'cantidad_bolsas_emp', 'cantidad_paquetes']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'w-full input'}),
            'descripcion': forms.TextInput(attrs={'class': 'w-full input'}),
            'cantidad': forms.NumberInput(attrs={'class': 'w-full input', 'step': '0.01'}),
            'sacos': forms.NumberInput(attrs={'class': 'w-full input', 'step': '1', 'min': '0'}),
            'cantidad_bolsas_emp': forms.NumberInput(attrs={'class': 'w-full input', 'step': '1', 'min': '0'}),
            'cantidad_paquetes': forms.NumberInput(attrs={'class': 'w-full input', 'step': '1', 'min': '0'}),
        }


@permiso_accion_requerido('inventario_cafe.view_inventariocafe', 'ver_inventario')
def listar_cafe(request):
    qs = (
        InventarioCafe.objects
        .select_related('cliente', 'estado_cafe', 'empaquecafe', 'origen', 'proceso_inven_cafe', 'variendad_inven_cafe')
        .only('id', 'cliente', 'estado_cafe', 'empaquecafe', 'origen', 'proceso_inven_cafe', 'variendad_inven_cafe', 'codigo', 'cantidad', 'sacos')
        .order_by('-id')
    )
    search = request.GET.get('q', '').strip()
    f_origen = request.GET.get('origen') or ''
    f_proceso = request.GET.get('proceso') or ''
    f_variedad = request.GET.get('variedad') or ''
    if search:
        qs = qs.filter(
            Q(codigo__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(cliente__nombre__icontains=search) |
            Q(cliente__apellidos__icontains=search) |
            Q(estado_cafe__estado_cafe__icontains=search) |
            Q(origen__origen__icontains=search) |
            Q(proceso_inven_cafe__proceso_inven_cafe__icontains=search) |
            Q(variendad_inven_cafe__variedad_cafe__icontains=search) |
            Q(empaquecafe__empaque_cafe__icontains=search)
        )

    if f_origen.isdigit():
        qs = qs.filter(origen_id=int(f_origen))
    if f_proceso.isdigit():
        qs = qs.filter(proceso_inven_cafe_id=int(f_proceso))
    if f_variedad.isdigit():
        qs = qs.filter(variendad_inven_cafe_id=int(f_variedad))

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
        'origenes': OrigenCafe.objects.all().order_by('origen'),
        'procesos': ProcesoInvenCafe.objects.all().order_by('proceso_inven_cafe'),
        'variedades': VariedadCafe.objects.all().order_by('variedad_cafe'),
        'f_origen': f_origen,
        'f_proceso': f_proceso,
        'f_variedad': f_variedad,
    }
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'inventario_cafe/_modal_listar_Cafe.html', ctx)
    return render(request, 'inventario_cafe/listar_Cafe.html', ctx)


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('inventario_cafe.add_inventariocafe', 'crear_inventario')
def add_cafe(request):
    if request.method == 'POST':
        form = InventarioCafeForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            # fecha_ingreso se usa solo para ordenar; no se muestra ni se ingresa
            if not obj.fecha_ingreso:
                obj.fecha_ingreso = timezone.now()
            obj.created_at = timezone.now()
            obj.updated_at = timezone.now()
            obj.save()
            preserve = {k: (request.GET.get(k) or request.POST.get(k)) for k in ['q','origen','proceso','variedad','page'] if (request.GET.get(k) or request.POST.get(k))}
            if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                qp = urlencode(preserve)
                url = f"{reverse('inventario_cafe_listar')}?fragment=1" + (f"&{qp}" if qp else '')
                return redirect(url)
            if preserve:
                return redirect(f"{reverse('inventario_cafe_listar')}?{urlencode(preserve)}")
            return redirect('inventario_cafe_listar')
    else:
        form = InventarioCafeForm()
    preserve = {k: request.GET.get(k) for k in ['q','origen','proceso','variedad','page'] if request.GET.get(k)}
    back_url = f"{reverse('inventario_cafe_listar')}?{urlencode(preserve)}" if preserve else reverse('inventario_cafe_listar')
    is_fragment = bool(request.headers.get('X-Fragment') or request.GET.get('fragment') == '1')
    # Variables individuales para plantillas (hidden inputs)
    ctx = {
        'form': form,
        'back_url': back_url,
        'is_fragment': is_fragment,
        'search': request.GET.get('q',''),
        'f_origen': request.GET.get('origen',''),
        'f_proceso': request.GET.get('proceso',''),
        'f_variedad': request.GET.get('variedad',''),
        'page_num': request.GET.get('page',''),
    }
    return render(request, 'inventario_cafe/add_Cafe.html', ctx)


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('inventario_cafe.change_inventariocafe', 'editar_inventario')
def edit_cafe(request, pk):
    obj = get_object_or_404(InventarioCafe, pk=pk)
    if request.method == 'POST':
        form = InventarioCafeForm(request.POST, instance=obj)
        if form.is_valid():
            inst = form.save(commit=False)
            inst.updated_at = timezone.now()
            inst.save()
            preserve = {k: (request.GET.get(k) or request.POST.get(k)) for k in ['q','origen','proceso','variedad','page'] if (request.GET.get(k) or request.POST.get(k))}
            if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                qp = urlencode(preserve)
                url = f"{reverse('inventario_cafe_listar')}?fragment=1" + (f"&{qp}" if qp else '')
                return redirect(url)
            if preserve:
                return redirect(f"{reverse('inventario_cafe_listar')}?{urlencode(preserve)}")
            return redirect('inventario_cafe_listar')
    else:
        form = InventarioCafeForm(instance=obj)
    preserve = {k: request.GET.get(k) for k in ['q','origen','proceso','variedad','page'] if request.GET.get(k)}
    back_url = f"{reverse('inventario_cafe_listar')}?{urlencode(preserve)}" if preserve else reverse('inventario_cafe_listar')
    is_fragment = bool(request.headers.get('X-Fragment') or request.GET.get('fragment') == '1')
    ctx = {
        'form': form,
        'obj': obj,
        'back_url': back_url,
        'is_fragment': is_fragment,
        'search': request.GET.get('q',''),
        'f_origen': request.GET.get('origen',''),
        'f_proceso': request.GET.get('proceso',''),
        'f_variedad': request.GET.get('variedad',''),
        'page_num': request.GET.get('page',''),
    }
    return render(request, 'inventario_cafe/detail_Cafe.html', ctx)


@permiso_accion_requerido('inventario_cafe.delete_inventariocafe', 'eliminar_inventario')
def delete_cafe(request, pk):
    obj = get_object_or_404(InventarioCafe, pk=pk)
    if request.method == 'POST':
        obj.delete()
        preserve = {k: (request.GET.get(k) or request.POST.get(k)) for k in ['q','origen','proceso','variedad','page'] if (request.GET.get(k) or request.POST.get(k))}
        if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
            qp = urlencode(preserve)
            url = f"{reverse('inventario_cafe_listar')}?fragment=1" + (f"&{qp}" if qp else '')
            return redirect(url)
        if preserve:
            return redirect(f"{reverse('inventario_cafe_listar')}?{urlencode(preserve)}")
        return redirect('inventario_cafe_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        ctx = {
            'obj': obj,
            'search': request.GET.get('q',''),
            'f_origen': request.GET.get('origen',''),
            'f_proceso': request.GET.get('proceso',''),
            'f_variedad': request.GET.get('variedad',''),
            'page_num': request.GET.get('page',''),
        }
        return render(request, 'inventario_cafe/confirm_delete_Cafe.html', ctx)
    return render(request, 'inventario_cafe/listar_Cafe.html', {})
