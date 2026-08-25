from django.shortcuts import render
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django import forms
from ordenes.models import Orden

from .models import Molienda


def molienda_deshabilitada(request):
    return HttpResponseForbidden("Módulo deshabilitado")


@permission_required('molienda.view_molienda', raise_exception=True)
def listar_molienda(request):
    return molienda_deshabilitada(request)
    qs = (
        Molienda.objects
        .select_related('orden__cliente', 'estado_tarea', 'nivel_molienda', 'estado_inven_cafe')
        .order_by('-id')
    )
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(orden__id__icontains=search) |
            Q(estado_tarea__estado_tareas__icontains=search) |
            Q(nivel_molienda__nivel_molienda__icontains=search) |
            Q(notas__icontains=search)
        )

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
        return render(request, 'molienda/_modal_listar_Molienda.html', ctx)
    return render(request, 'molienda/listar_Molienda.html', ctx)


class OrdenChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return str(obj)


class MoliendaForm(forms.ModelForm):
    orden = OrdenChoiceField(queryset=Orden.objects.none(), required=False, widget=forms.Select(attrs={'class': 'w-full select'}))
    class Meta:
        model = Molienda
        fields = ['orden', 'estado_tarea', 'nivel_molienda', 'estado_inven_cafe', 'peso_moler', 'notas']
        widgets = {
            'estado_tarea': forms.Select(attrs={'class': 'w-full select'}),
            'nivel_molienda': forms.Select(attrs={'class': 'w-full select'}),
            'estado_inven_cafe': forms.Select(attrs={'class': 'w-full select'}),
            'peso_moler': forms.NumberInput(attrs={'class': 'w-full input'}),
            'notas': forms.TextInput(attrs={'class': 'w-full input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_qs = Orden.objects.all().order_by('-id')
        if self.is_bound:
            self.fields['orden'].queryset = base_qs
        else:
            self.fields['orden'].queryset = base_qs.select_related('cliente')[:200]
        self.fields['orden'].empty_label = 'Seleccione una orden'


@permission_required('molienda.add_molienda', raise_exception=True)
def add_molienda(request):
    return molienda_deshabilitada(request)
    if request.method == 'POST':
        form = MoliendaForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                    return listar_molienda(request)
                return redirect('molienda_listar')
    else:
        form = MoliendaForm()
    if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
        return render(request, 'molienda/add_Molienda.html', {'form': form})
    return render(request, 'molienda/listar_Molienda.html', {})


@permission_required('molienda.change_molienda', raise_exception=True)
def edit_molienda(request, pk):
    return molienda_deshabilitada(request)
    obj = get_object_or_404(Molienda, pk=pk)
    if request.method == 'POST':
        form = MoliendaForm(request.POST, instance=obj)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                form.add_error(None, f"Error al guardar: {e}")
            else:
                if request.headers.get('X-Fragment'):
                    return listar_molienda(request)
                return redirect('molienda_listar')
    else:
        form = MoliendaForm(instance=obj)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'molienda/detail_Molienda.html', {'form': form, 'obj': obj})
    return render(request, 'molienda/listar_Molienda.html', {})


@permission_required('molienda.delete_molienda', raise_exception=True)
def delete_molienda(request, pk):
    return molienda_deshabilitada(request)
    obj = get_object_or_404(Molienda, pk=pk)
    if request.method == 'POST':
        obj.delete()
        if request.headers.get('X-Fragment'):
            return listar_molienda(request)
        return redirect('molienda_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'molienda/confirm_delete_Molienda.html', {'obj': obj})
    return render(request, 'molienda/listar_Molienda.html', {})
