from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from seguridad.decorators import permiso_accion_requerido
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django import forms
from django.utils import timezone
import re

from .models import SeleccionTueste
from ordenes.forms import enforce_parent_order_not_completed
from ordenes.models import Orden
from seguridad.helpers import puede_editar_campo
from seguridad.models import PermisoCampo
from estado_tareas.models import EstadoTarea
from clientes.models import Cliente


MODELO_PERMISO_SELECCION_TUESTE = 'SeleccionTueste'
CAMPO_PESO_GRUPO_TOSTADOR = {'peso_grupo1', 'peso_grupo2', 'peso_grupo3'}


class OrdenChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        try:
            return str(obj)
        except Exception:
            return f"Orden {getattr(obj, 'pk', '')}"


class SeleccionTuesteForm(forms.ModelForm):
    orden = OrdenChoiceField(queryset=Orden.objects.none(), required=False, widget=forms.Select(attrs={'class':'w-full select'}))
    cliente = forms.ModelChoiceField(queryset=Cliente.objects.none(), required=False, disabled=True, widget=forms.Select(attrs={'class':'w-full select'}))
    estado_tareas = forms.ModelChoiceField(queryset=EstadoTarea.objects.all().order_by('estado_tareas'), required=False, widget=forms.Select(attrs={'class':'w-full select'}))

    class Meta:
        model = SeleccionTueste
        fields = [
            'orden','estado_tareas',
            'cat_limpieza','cat_quaker','peso_quaker',
            'cat_grupo1','desc_grupo1','peso_grupo1',
            'cat_grupo2','desc_grupo2','peso_grupo2',
            'cat_grupo3','desc_grupo3','peso_grupo3',
            'notas',
        ]
        widgets = {
            'cat_limpieza': forms.CheckboxInput(attrs={'class':'toggle'}),
            'cat_quaker': forms.CheckboxInput(attrs={'class':'toggle'}),
            'peso_quaker': forms.NumberInput(attrs={'class':'w-full input','step':'0.01'}),
            'cat_grupo1': forms.CheckboxInput(attrs={'class':'toggle'}),
            'desc_grupo1': forms.TextInput(attrs={'class':'w-full input'}),
            'peso_grupo1': forms.NumberInput(attrs={'class':'w-full input','step':'0.01'}),
            'cat_grupo2': forms.CheckboxInput(attrs={'class':'toggle'}),
            'desc_grupo2': forms.TextInput(attrs={'class':'w-full input'}),
            'peso_grupo2': forms.NumberInput(attrs={'class':'w-full input','step':'0.01'}),
            'cat_grupo3': forms.CheckboxInput(attrs={'class':'toggle'}),
            'desc_grupo3': forms.TextInput(attrs={'class':'w-full input'}),
            'peso_grupo3': forms.NumberInput(attrs={'class':'w-full input','step':'0.01'}),
            'notas': forms.Textarea(attrs={'class':'w-full textarea','rows':'3','maxlength':'500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_qs = Orden.objects.filter(selec_cafe_tostado=True).order_by('-id')
        estado_pendiente = EstadoTarea.objects.filter(estado_tareas__iexact='Pendiente').order_by('id').first()
        self.fields['cliente'].queryset = Cliente.objects.all().order_by('nombre', 'apellidos', 'id')
        if self.is_bound:
            self.fields['orden'].queryset = base_qs
        else:
            self.fields['orden'].queryset = base_qs.select_related('cliente')[:200]
        self.fields['orden'].empty_label = 'Seleccione una orden'
        self.fields['cliente'].empty_label = 'Seleccione un cliente'
        cliente = None
        orden_id = self.data.get('orden') if self.is_bound else None
        if orden_id:
            try:
                cliente = base_qs.select_related('cliente').get(pk=orden_id).cliente
            except (TypeError, ValueError, Orden.DoesNotExist):
                cliente = None
        elif getattr(self.instance, 'orden', None) is not None:
            cliente = getattr(self.instance.orden, 'cliente', None)
        if cliente is not None:
            self.fields['cliente'].initial = cliente.pk
            self.initial['cliente'] = cliente.pk
        if estado_pendiente is not None and not getattr(self.instance, 'pk', None) and not self.is_bound:
            self.fields['estado_tareas'].initial = estado_pendiente.pk
            self.initial['estado_tareas'] = estado_pendiente.pk

    def clean_orden(self):
        orden = self.cleaned_data.get('orden')
        if orden and not getattr(orden, 'selec_cafe_tostado', False):
            raise forms.ValidationError('Solo se permiten órdenes de producción con selección tostado habilitada.')
        return orden

    def clean(self):
        cleaned_data = super().clean()
        if not enforce_parent_order_not_completed(self):
            return cleaned_data

        estado_tareas = cleaned_data.get('estado_tareas')
        estado_nombre = (getattr(estado_tareas, 'estado_tareas', '') or '').strip().lower()
        es_completada = estado_nombre == 'completada'

        cat_quaker = bool(cleaned_data.get('cat_quaker'))
        peso_quaker = cleaned_data.get('peso_quaker')
        cat_grupo1 = bool(cleaned_data.get('cat_grupo1'))
        peso_grupo1 = cleaned_data.get('peso_grupo1')
        cat_grupo2 = bool(cleaned_data.get('cat_grupo2'))
        peso_grupo2 = cleaned_data.get('peso_grupo2')
        cat_grupo3 = bool(cleaned_data.get('cat_grupo3'))
        peso_grupo3 = cleaned_data.get('peso_grupo3')
        desc_grupo1 = (cleaned_data.get('desc_grupo1') or '').strip()
        desc_grupo2 = (cleaned_data.get('desc_grupo2') or '').strip()
        desc_grupo3 = (cleaned_data.get('desc_grupo3') or '').strip()

        cleaned_data['desc_grupo1'] = desc_grupo1 or None
        cleaned_data['desc_grupo2'] = desc_grupo2 or None
        cleaned_data['desc_grupo3'] = desc_grupo3 or None

        if es_completada:
            if cat_quaker and (peso_quaker is None or peso_quaker <= 0):
                self.add_error('peso_quaker', 'Debe ingresar un Peso Quaker mayor a cero para completar la tarea.')

            if cat_grupo1 and (not desc_grupo1 or peso_grupo1 is None or peso_grupo1 <= 0):
                self.add_error('desc_grupo1', 'Debe ingresar la descripción y un Peso del Grupo 1 mayor a cero.')

            if cat_grupo2 and (not desc_grupo2 or peso_grupo2 is None or peso_grupo2 <= 0):
                self.add_error('desc_grupo2', 'Debe ingresar la descripción y un Peso del Grupo 2 mayor a cero.')

            if cat_grupo3 and (not desc_grupo3 or peso_grupo3 is None or peso_grupo3 <= 0):
                self.add_error('desc_grupo3', 'Debe ingresar la descripción y un Peso del Grupo 3 mayor a cero.')

        return cleaned_data


def _build_orden_seleccion_tueste_defaults(orden):
    cliente = getattr(orden, 'cliente', None)

    return {
        'cliente_id': getattr(cliente, 'id', None),
        'cliente_label': str(cliente) if cliente is not None else '',
    }


@require_http_methods(["GET"])
@permiso_accion_requerido('seleccion_tueste.add_selecciontueste', 'crear_orden_seleccion_tueste')
def orden_seleccion_tueste_defaults(request):
    orden_id = request.GET.get('orden_id')
    if not orden_id:
        return JsonResponse(_build_orden_seleccion_tueste_defaults(Orden()))

    try:
        orden = Orden.objects.select_related('cliente').get(pk=orden_id, selec_cafe_tostado=True)
    except (TypeError, ValueError, Orden.DoesNotExist):
        return JsonResponse({'detail': 'Orden no encontrada.'}, status=404)

    return JsonResponse(_build_orden_seleccion_tueste_defaults(orden))


def obtener_rol_usuario(user):
    perfil = getattr(user, 'perfilusuario', None) or getattr(user, 'profile', None)
    rol = getattr(perfil, 'rol', None)
    if rol is not None:
        return rol
    return None


def es_tostador(user) -> bool:
    rol = obtener_rol_usuario(user)
    nombre = getattr(rol, 'nombre', '')
    return str(nombre).strip().lower() == 'tostador'


def campos_editables_tostador(user):
    rol = obtener_rol_usuario(user)
    if rol is None:
        return set()

    configurados = set(
        PermisoCampo.objects.filter(rol=rol, modelo=MODELO_PERMISO_SELECCION_TUESTE, campo__in=CAMPO_PESO_GRUPO_TOSTADOR)
        .values_list('campo', flat=True)
        .distinct()
    )

    editables = set()
    for campo in CAMPO_PESO_GRUPO_TOSTADOR:
        if campo not in configurados or puede_editar_campo(user, MODELO_PERMISO_SELECCION_TUESTE, campo):
            editables.add(campo)

    return editables


def aplicar_restricciones_form_tostador(form):
    user = getattr(form, '_request_user', None)
    campos_editables = campos_editables_tostador(user) if user is not None else set()

    for field_name, field in form.fields.items():
        css = field.widget.attrs.get('class', '')
        if field_name in campos_editables:
            field.disabled = False
            field.widget.attrs.pop('disabled', None)
            field.widget.attrs.pop('readonly', None)
            field.widget.attrs['class'] = f"{css} ring-1 ring-brand-primary/30".strip()
            continue

        field.disabled = True
        field.widget.attrs['disabled'] = 'disabled'
        field.widget.attrs['aria-readonly'] = 'true'
        field.widget.attrs['class'] = f"{css} bg-gray-100 text-gray-500 cursor-not-allowed opacity-90".strip()


def proteger_campos_tostador(obj, original):
    campos_editables = campos_editables_tostador(getattr(obj, '_request_user', None))
    for campo in SeleccionTuesteForm.Meta.fields:
        if campo in campos_editables:
            continue
        setattr(obj, campo, getattr(original, campo))


def construir_contexto_seleccion_tueste(request, obj, form=None):
    user_is_tostador = es_tostador(request.user)
    form = form or SeleccionTuesteForm(instance=obj)
    form._request_user = request.user
    if user_is_tostador:
        aplicar_restricciones_form_tostador(form)

    return {
        'form': form,
        'obj': obj,
        'user_is_tostador': user_is_tostador,
    }


def render_editar_seleccion_tueste(request, obj, form=None):
    return render(
        request,
        'seleccion_tueste/detail_OrdenesSeleccionTueste.html',
        construir_contexto_seleccion_tueste(request, obj, form=form),
    )


@permiso_accion_requerido('seleccion_tueste.view_selecciontueste', 'ver_orden_seleccion_tueste')
def listar_ordenes_seleccion_tueste(request):
    qs = (
        SeleccionTueste.objects
        .select_related('orden__cliente', 'estado_tareas')
        .only(
            'id', 'orden', 'orden__orden', 'orden__cliente', 'estado_tareas',
            'cat_limpieza', 'cat_quaker', 'peso_quaker',
            'cat_grupo1', 'desc_grupo1', 'peso_grupo1',
            'cat_grupo2', 'desc_grupo2', 'peso_grupo2',
            'cat_grupo3', 'desc_grupo3', 'peso_grupo3',
        )
    )
    search = request.GET.get('q','').strip()
    if search:
        s = search.strip()
        filters = (
            Q(orden__cliente__nombre__icontains=s) |
            Q(orden__cliente__apellidos__icontains=s)
        )
        m = re.search(r"(?:^|\b)orden\s*(\d+)\b", s, flags=re.IGNORECASE)
        if m:
            filters |= Q(orden__orden__icontains=m.group(1))
        else:
            m2 = re.search(r"\b(\d+)\b", s)
            if m2:
                filters |= Q(orden__orden__icontains=m2.group(1))
        qs = qs.filter(filters)

    qs = qs.order_by('-fecha_ingreso','-id')

    paginator = Paginator(qs, 7)
    page = request.GET.get('page')
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    ctx = {
        'selecciones': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'search': search,
    }
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'seleccion_tueste/_modal_listar_OrdenesSeleccionTueste.html', ctx)
    return render(request, 'seleccion_tueste/listar_OrdenesSeleccionTueste.html', ctx)


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('seleccion_tueste.add_selecciontueste', 'crear_orden_seleccion_tueste')
def add_orden_seleccion_tueste(request):
    if request.method == 'POST':
        form = SeleccionTuesteForm(request.POST)
        if form.is_valid():
            if not enforce_parent_order_not_completed(form):
                return render(request, 'seleccion_tueste/add_OrdenesSeleccionTueste.html', {'form': form})
            obj = form.save(commit=False)
            if not obj.fecha_ingreso:
                obj.fecha_ingreso = timezone.now()
            obj.created_at = timezone.now()
            obj.updated_at = timezone.now()
            obj.save()
            if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                return listar_ordenes_seleccion_tueste(request)
            return redirect('ordenes_seleccion_tueste_listar')
    else:
        form = SeleccionTuesteForm()
    if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
        return render(request, 'seleccion_tueste/add_OrdenesSeleccionTueste.html', {'form': form})
    return render(request, 'seleccion_tueste/listar_OrdenesSeleccionTueste.html', {})


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('seleccion_tueste.change_selecciontueste', 'editar_orden_seleccion_tueste')
def edit_orden_seleccion_tueste(request, pk):
    obj = get_object_or_404(SeleccionTueste, pk=pk)
    user_is_tostador = es_tostador(request.user)

    if request.method == 'POST':
        form = SeleccionTuesteForm(request.POST, instance=obj)
        form._request_user = request.user
        if user_is_tostador:
            aplicar_restricciones_form_tostador(form)
        if form.is_valid():
            if not enforce_parent_order_not_completed(form):
                return render_editar_seleccion_tueste(request, obj, form=form)
            inst = form.save(commit=False)
            inst._request_user = request.user
            if user_is_tostador:
                proteger_campos_tostador(inst, obj)
            inst.updated_at = timezone.now()
            inst.save()
            if request.headers.get('X-Fragment'):
                return listar_ordenes_seleccion_tueste(request)
            return redirect('ordenes_seleccion_tueste_listar')
    else:
        form = SeleccionTuesteForm(instance=obj)
        form._request_user = request.user
        if user_is_tostador:
            aplicar_restricciones_form_tostador(form)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render_editar_seleccion_tueste(request, obj, form=form)
    return render(request, 'seleccion_tueste/listar_OrdenesSeleccionTueste.html', {})


@permiso_accion_requerido('seleccion_tueste.delete_selecciontueste', 'eliminar_orden_seleccion_tueste')
def delete_orden_seleccion_tueste(request, pk):
    obj = get_object_or_404(SeleccionTueste, pk=pk)
    if request.method == 'POST':
        obj.delete()
        if request.headers.get('X-Fragment'):
            return listar_ordenes_seleccion_tueste(request)
        return redirect('ordenes_seleccion_tueste_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'seleccion_tueste/confirm_delete_OrdenesSeleccionTueste.html', {'t': obj})
    return render(request, 'seleccion_tueste/listar_OrdenesSeleccionTueste.html', {})
