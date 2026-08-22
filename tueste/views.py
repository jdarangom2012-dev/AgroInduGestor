from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.db.models import Q, Sum
from django import forms
from django.utils import timezone
import re
from uuid import uuid4

from .models import DetalleTueste, Tueste
from clientes.models import Cliente
from estado_ordenes.models import EstadoOrden
from ordenes.forms import enforce_parent_order_not_completed
from ordenes.models import Orden
from seguridad.decorators import permiso_accion_requerido
from seguridad.helpers import puede_editar_campo, tiene_permiso_accion
from seguridad.models import PermisoCampo
from estado_tareas.models import EstadoTarea
from nivel_tueste.models import NivelTueste
from inventario_cafe.models import InventarioCafe


COMPLETADA_BATCHES_PENDIENTES_ERROR = 'No es posible completar la Orden de Tueste porque existen batches pendientes de finalizar. Todos los batches deben estar en estado Completada antes de completar la orden.'
COMPLETADA_PESOS_ERROR = 'No es posible completar la Orden de Tueste porque el Peso Café Verde Total o el Peso Café Tostado Total son menores o iguales a cero.'
KILOS_VERDES_BATCHES_REQUERIDOS_ERROR = 'Todos los batches deben tener un valor de Kilos Verdes mayor a cero para crear la Orden de Tueste.'


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
    campos_base = {'peso_cafe_vede_total', 'peso_cafe_tostado_total'}
    rol = obtener_rol_usuario(user)
    if rol is None:
        return set()

    configurados = set(
        PermisoCampo.objects.filter(rol=rol, modelo='Tueste', campo__in=campos_base)
        .values_list('campo', flat=True)
        .distinct()
    )

    editables = set()
    for campo in campos_base:
        if campo not in configurados or puede_editar_campo(user, 'Tueste', campo):
            editables.add(campo)

    return editables


def aplicar_restricciones_form_tostador(form):
    user = getattr(form, '_request_user', None)
    campos_editables = campos_editables_tostador(user) if user is not None else set()

    for field_name, field in form.fields.items():
        if field_name in campos_editables:
            field.disabled = False
            field.widget.attrs.pop('disabled', None)
            field.widget.attrs.pop('readonly', None)
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{css} ring-1 ring-brand-primary/30".strip()
            continue

        if getattr(field.widget, 'input_type', '') in {'select', 'selectmultiple', 'checkbox', 'radio', 'file'}:
            field.disabled = True
            field.widget.attrs['disabled'] = 'disabled'
        else:
            field.widget.attrs['readonly'] = 'readonly'

        css = field.widget.attrs.get('class', '')
        field.widget.attrs['class'] = f"{css} bg-gray-100 text-gray-500 cursor-not-allowed".strip()
        field.widget.attrs['aria-readonly'] = 'true'


def proteger_campos_tostador(obj, original):
    campos_editables = campos_editables_tostador(getattr(obj, '_request_user', None))
    campos_protegidos = [
        'orden',
        'inventario_cafe_ref',
        'estado_tareas',
        'nivel_tueste',
        'batche',
        'peso_cafe_vede',
        'peso_cafe_tostado',
        'peso_cafe_vede_total',
        'peso_cafe_tostado_total',
        'notas',
        'notas_op',
    ]

    for campo in campos_protegidos:
        if campo in campos_editables:
            continue
        setattr(obj, campo, getattr(original, campo))


def calcular_rendimiento_tueste(peso_verde_total, peso_tostado_total):
    try:
        verde = float(peso_verde_total or 0)
    except (TypeError, ValueError):
        verde = 0.0

    try:
        tostado = float(peso_tostado_total or 0)
    except (TypeError, ValueError):
        tostado = 0.0

    if tostado == 0:
        return 0.0

    return round((verde / tostado) * 100, 2)


def pesos_completan_tueste(peso_verde_total, peso_tostado_total):
    try:
        verde = float(peso_verde_total or 0)
    except (TypeError, ValueError):
        verde = 0.0

    try:
        tostado = float(peso_tostado_total or 0)
    except (TypeError, ValueError):
        tostado = 0.0

    return verde > 0 and tostado > 0


def obtener_estado_tarea_completada():
    return EstadoTarea.objects.filter(estado_tareas__iexact='Completada').first()


def recalcular_totales_tueste_desde_batches(tueste):
    totales = tueste.batches.aggregate(
        peso_verde_total=Sum('kilos_verde'),
        peso_tostado_total=Sum('kilos_tostado'),
    )
    tueste.peso_cafe_vede_total = float(totales.get('peso_verde_total') or 0)
    tueste.peso_cafe_tostado_total = float(totales.get('peso_tostado_total') or 0)
    tueste.rendimiento = calcular_rendimiento_tueste(
        tueste.peso_cafe_vede_total,
        tueste.peso_cafe_tostado_total,
    )
    tueste.updated_at = timezone.now()
    tueste.save(update_fields=[
        'peso_cafe_vede_total',
        'peso_cafe_tostado_total',
        'rendimiento',
        'updated_at',
    ])


def respuesta_guardado_batch(request):
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return listar_ordenes_tueste(request)
    return redirect('ordenes_tueste_listar')


def respuesta_guardado_batch_en_modal_padre(request, tueste):
    detalle_batches = tueste.batches.select_related('estado_orden', 'nivel_tueste').all()
    form = TuesteForm(instance=tueste)
    form._request_user = request.user
    if es_tostador(request.user):
        aplicar_restricciones_form_tostador(form)

    response = render(request, 'tueste/detail_OrdenesTueste.html', {
        'form': form,
        'tueste': tueste,
        'detalle_batches': detalle_batches,
    })
    response['X-Modal-Update-Parent'] = '1'
    return response


def tiene_campos_editables(user, objeto) -> bool:
    if getattr(user, 'is_superuser', False):
        return True

    if not objeto:
        return False

    modelo_perm = 'Tueste'
    campos_perm = [
        'orden',
        'inventario_cafe_ref',
        'estado_tareas',
        'nivel_tueste',
        'rendimiento',
        'peso_cafe_vede_total',
        'peso_cafe_tostado_total',
        'notas',
        'notas_op',
    ]

    configurados = set(
        PermisoCampo.objects.filter(modelo=modelo_perm, campo__in=campos_perm)
        .values_list('campo', flat=True)
        .distinct()
    )

    for campo in campos_perm:
        # Compatibilidad histórica: si el campo no tiene configuración explícita, se considera editable.
        if campo not in configurados:
            return True
        if puede_editar_campo(user, modelo_perm, campo):
            return True

    return False


class OrdenChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return str(obj)


class InventarioChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.codigo or f"INV-{obj.id:06d}"


class TuesteForm(forms.ModelForm):
    orden = OrdenChoiceField(queryset=Orden.objects.none(), required=False, widget=forms.Select(attrs={'class':'w-full select'}))
    cliente = forms.ModelChoiceField(queryset=Cliente.objects.none(), required=False, disabled=True, widget=forms.Select(attrs={'class':'w-full select'}))
    estado_tareas = forms.ModelChoiceField(queryset=EstadoTarea.objects.all().order_by('estado_tareas'), required=False, widget=forms.Select(attrs={'class':'w-full select'}))
    nivel_tueste = forms.ModelChoiceField(queryset=NivelTueste.objects.all().order_by('nivel_tueste'), required=False, widget=forms.Select(attrs={'class':'w-full select'}))
    inventario_cafe_ref = InventarioChoiceField(queryset=InventarioCafe.objects.all().order_by('-id'), required=False, widget=forms.Select(attrs={'class':'w-full select'}))

    class Meta:
        model = Tueste
        # fecha_ingreso es automática; no se expone en el formulario
        fields = ['orden','inventario_cafe_ref','estado_tareas','nivel_tueste','batche','peso_cafe_vede','peso_cafe_tostado','rendimiento','peso_cafe_vede_total','peso_cafe_tostado_total','notas','notas_op']
        widgets = {
            'batche': forms.NumberInput(attrs={'class':'w-full input', 'step':'1', 'min':'0'}),
            'peso_cafe_vede': forms.NumberInput(attrs={'class':'w-full input', 'step':'0.01'}),
            'peso_cafe_tostado': forms.NumberInput(attrs={'class':'w-full input', 'step':'0.01'}),
            'rendimiento': forms.NumberInput(attrs={'class':'w-full input', 'step':'0.01', 'readonly':'readonly'}),
            'peso_cafe_vede_total': forms.NumberInput(attrs={'class':'w-full input', 'step':'0.01'}),
            'peso_cafe_tostado_total': forms.NumberInput(attrs={'class':'w-full input', 'step':'0.01'}),
            'notas': forms.TextInput(attrs={'class':'w-full input'}),
            'notas_op': forms.TextInput(attrs={'class':'w-full input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_qs = Orden.objects.all().order_by('-id')
        estado_pendiente = EstadoTarea.objects.filter(estado_tareas__iexact='Pendiente').order_by('id').first()
        self.fields['cliente'].queryset = Cliente.objects.all().order_by('nombre', 'apellidos', 'id')
        if self.is_bound:
            self.fields['orden'].queryset = base_qs
        else:
            self.fields['orden'].queryset = base_qs.select_related('cliente')[:200]
        self.fields['orden'].empty_label = 'Seleccione una orden'
        self.fields['inventario_cafe_ref'].empty_label = 'Seleccione un café'
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

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.batche = 0
        instance.peso_cafe_vede = 0
        instance.peso_cafe_tostado = 0

        if commit:
            instance.save()

        return instance

    def clean(self):
        cleaned_data = super().clean()
        if not enforce_parent_order_not_completed(self):
            return cleaned_data

        if not getattr(self.instance, 'pk', None):
            nivel_tueste = cleaned_data.get('nivel_tueste')
            peso_verde_total = cleaned_data.get('peso_cafe_vede_total')

            if not nivel_tueste:
                self.add_error('nivel_tueste', 'Debe seleccionar un Nivel de Tueste.')

            try:
                peso_valor = float(peso_verde_total)
            except (TypeError, ValueError):
                peso_valor = 0.0

            if peso_verde_total is None or peso_valor <= 0:
                self.add_error('peso_cafe_vede_total', 'El Peso Café Verde Total debe ser mayor que cero.')

            if self.errors:
                return cleaned_data

        if getattr(self.instance, 'pk', None) and self.instance.batches.filter(
            Q(kilos_verde__isnull=True) | Q(kilos_verde__lte=0)
        ).exists():
            raise forms.ValidationError(KILOS_VERDES_BATCHES_REQUERIDOS_ERROR)

        estado_tareas = cleaned_data.get('estado_tareas')
        estado_nombre = (getattr(estado_tareas, 'estado_tareas', '') or '').strip().lower()
        if estado_nombre != 'completada':
            return cleaned_data

        peso_verde_total = cleaned_data.get('peso_cafe_vede_total')
        peso_tostado_total = cleaned_data.get('peso_cafe_tostado_total')
        if not pesos_completan_tueste(peso_verde_total, peso_tostado_total):
            raise forms.ValidationError(COMPLETADA_PESOS_ERROR)

        if getattr(self.instance, 'pk', None) and self.instance.batches.exclude(estado_orden__estado_orden__iexact='Completada').exists():
            raise forms.ValidationError(COMPLETADA_BATCHES_PENDIENTES_ERROR)

        return cleaned_data


class BatchTuesteForm(forms.ModelForm):
    estado_orden = forms.ModelChoiceField(queryset=EstadoOrden.objects.all().order_by('estado_orden'), required=False, widget=forms.Select(attrs={'class':'w-full select'}))
    nivel_tueste = forms.ModelChoiceField(queryset=NivelTueste.objects.all().order_by('nivel_tueste'), required=False, widget=forms.Select(attrs={'class':'w-full select'}))

    class Meta:
        model = DetalleTueste
        fields = ['estado_orden', 'nivel_tueste', 'kilos_verde', 'kilos_tostado', 'observaciones']
        widgets = {
            'kilos_verde': forms.NumberInput(attrs={'class':'w-full input', 'step':'0.01'}),
            'kilos_tostado': forms.NumberInput(attrs={'class':'w-full input', 'step':'0.01'}),
            'observaciones': forms.TextInput(attrs={'class':'w-full input', 'maxlength':'500'}),
        }


def _build_orden_tueste_defaults(orden):
    cliente = getattr(orden, 'cliente', None)
    inventario = getattr(orden, 'id_inven_cafe', None)
    estado_pendiente = EstadoTarea.objects.filter(estado_tareas__iexact='Pendiente').order_by('id').first()

    return {
        'cliente_id': getattr(cliente, 'id', None),
        'cliente_label': str(cliente) if cliente is not None else '',
        'inventario_cafe_ref_id': getattr(inventario, 'id', None),
        'inventario_cafe_ref_label': str(inventario) if inventario is not None else '',
        'estado_tareas_id': getattr(estado_pendiente, 'id', None),
        'estado_tareas_label': getattr(estado_pendiente, 'estado_tareas', '') if estado_pendiente is not None else '',
    }


@require_http_methods(["GET"])
@permiso_accion_requerido('tueste.add_tueste', 'crear_orden_tueste')
def orden_tueste_defaults(request):
    orden_id = request.GET.get('orden_id')
    if not orden_id:
        return JsonResponse(_build_orden_tueste_defaults(Orden()))

    try:
        orden = Orden.objects.select_related('cliente', 'id_inven_cafe').get(pk=orden_id)
    except (TypeError, ValueError, Orden.DoesNotExist):
        return JsonResponse({'detail': 'Orden no encontrada.'}, status=404)

    return JsonResponse(_build_orden_tueste_defaults(orden))


@permiso_accion_requerido('tueste.view_tueste', 'ver_orden_tueste')
def listar_ordenes_tueste(request):
    qs = Tueste.objects.select_related('orden__cliente','estado_tareas','nivel_tueste','inventario_cafe_ref')
    search = request.GET.get('q','').strip()
    if search:
        s = search.strip()
        filters = (
            Q(orden__cliente__nombre__icontains=s) |
            Q(orden__cliente__apellidos__icontains=s)
        )
        m = re.search(r"(?:^|\b)orden\s*(\d+)\b", s, flags=re.IGNORECASE)
        if m:
            try:
                filters |= Q(orden__id=int(m.group(1)))
            except ValueError:
                pass
        else:
            m2 = re.search(r"\b(\d+)\b", s)
            if m2:
                try:
                    filters |= Q(orden__id=int(m2.group(1)))
                except ValueError:
                    pass
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

    puede_editar_tueste = tiene_permiso_accion(request.user, django_perm='tueste.change_tueste', codigo='editar_orden_tueste')
    puede_eliminar_tueste = tiene_permiso_accion(request.user, django_perm='tueste.delete_tueste', codigo='eliminar_orden_tueste')

    for tueste in page_obj.object_list:
        tueste.puede_editar = puede_editar_tueste and tiene_campos_editables(request.user, tueste)
        tueste.puede_eliminar = puede_eliminar_tueste

    ctx = {
        'tuestes': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'search': search,
        'puede_editar_tueste': puede_editar_tueste,
        'puede_eliminar_tueste': puede_eliminar_tueste,
    }
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'tueste/_modal_listar_OrdenesTueste.html', ctx)
    return render(request, 'tueste/listar_OrdenesTueste.html', ctx)


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('tueste.add_tueste', 'crear_orden_tueste')
def add_orden_tueste(request):
    is_fragment = request.headers.get('X-Fragment') or request.GET.get('fragment') == '1'

    def new_submit_token():
        return uuid4().hex

    def render_form(form):
        return render(request, 'tueste/add_OrdenesTueste.html', {
            'form': form,
            'detalle_batches': [],
            'submit_token': new_submit_token(),
        })

    def duplicate_response():
        if is_fragment:
            return listar_ordenes_tueste(request)
        return redirect('ordenes_tueste_listar')

    if request.method == 'POST':
        form = TuesteForm(request.POST)
        if form.is_valid():
            if not enforce_parent_order_not_completed(form):
                return render_form(form)
            submitted_flag = request.POST.get('_submitted')
            submission_token = request.POST.get('_submission_token', '').strip()

            if submitted_flag == '1':
                token_key = f"tueste:add:submit:{submission_token}"
                if not submission_token or not cache.add(token_key, True, timeout=300):
                    return duplicate_response()

            obj = form.save(commit=False)
            obj.rendimiento = calcular_rendimiento_tueste(
                obj.peso_cafe_vede_total,
                obj.peso_cafe_tostado_total,
            )
            from django.utils import timezone
            obj.fecha_ingreso = timezone.now()
            obj.created_at = timezone.now()
            obj.updated_at = timezone.now()
            obj.save()
            if is_fragment:
                return listar_ordenes_tueste(request)
            return redirect('ordenes_tueste_listar')
    else:
        form = TuesteForm()
    if is_fragment:
        return render_form(form)
    return render(request, 'tueste/listar_OrdenesTueste.html', {})


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('tueste.change_tueste', 'editar_orden_tueste')
def edit_orden_tueste(request, pk):
    tueste = get_object_or_404(Tueste, pk=pk)
    user_is_tostador = es_tostador(request.user)
    detalle_batches = tueste.batches.select_related('estado_orden', 'nivel_tueste').all()

    if request.method == 'POST':
        form = TuesteForm(request.POST, instance=tueste)
        form._request_user = request.user
        if form.is_valid():
            if not enforce_parent_order_not_completed(form):
                if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
                    return render(request, 'tueste/detail_OrdenesTueste.html', {'form': form, 'tueste': tueste, 'detalle_batches': detalle_batches})
                return render(request, 'tueste/listar_OrdenesTueste.html', {})
            obj = form.save(commit=False)
            obj._request_user = request.user
            if user_is_tostador:
                proteger_campos_tostador(obj, tueste)
            obj.rendimiento = calcular_rendimiento_tueste(
                obj.peso_cafe_vede_total,
                obj.peso_cafe_tostado_total,
            )
            if obj.pk and pesos_completan_tueste(
                obj.peso_cafe_vede_total,
                obj.peso_cafe_tostado_total,
            ):
                if obj.batches.exclude(estado_orden__estado_orden__iexact='Completada').exists():
                    form.add_error(None, COMPLETADA_BATCHES_PENDIENTES_ERROR)
                else:
                    estado_completada = obtener_estado_tarea_completada()
                    if estado_completada is not None:
                        obj.estado_tareas = estado_completada
            if form.errors:
                if user_is_tostador:
                    aplicar_restricciones_form_tostador(form)
                if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
                    return render(request, 'tueste/detail_OrdenesTueste.html', {'form': form, 'tueste': tueste, 'detalle_batches': detalle_batches})
                return render(request, 'tueste/listar_OrdenesTueste.html', {})
            obj.updated_at = timezone.now()
            obj.save()
            if request.headers.get('X-Fragment'):
                return listar_ordenes_tueste(request)
            return redirect('ordenes_tueste_listar')
    else:
        form = TuesteForm(instance=tueste)
        form._request_user = request.user

    if user_is_tostador:
        aplicar_restricciones_form_tostador(form)

    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'tueste/detail_OrdenesTueste.html', {'form': form, 'tueste': tueste, 'detalle_batches': detalle_batches})
    return render(request, 'tueste/listar_OrdenesTueste.html', {})


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('tueste.change_tueste', 'editar_orden_tueste')
def add_batch_tueste(request, pk):
    tueste = get_object_or_404(Tueste, pk=pk)
    numero_batch = (tueste.batches.order_by('-numero_batch').values_list('numero_batch', flat=True).first() or 0) + 1

    if request.method == 'POST':
        form = BatchTuesteForm(request.POST)
        if form.is_valid():
            detalle = form.save(commit=False)
            detalle.tueste = tueste
            detalle.numero_batch = numero_batch
            if not detalle.fecha_ingreso:
                detalle.fecha_ingreso = timezone.now()
            detalle.save()
            recalcular_totales_tueste_desde_batches(tueste)
            tueste.refresh_from_db()
            if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
                return respuesta_guardado_batch_en_modal_padre(request, tueste)
            return respuesta_guardado_batch(request)
    else:
        form = BatchTuesteForm()

    return render(request, 'tueste/batch_OrdenesTueste.html', {
        'form': form,
        'tueste': tueste,
        'numero_batch': numero_batch,
    })


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('tueste.change_tueste', 'editar_orden_tueste')
def edit_batch_tueste(request, pk, detalle_pk):
    tueste = get_object_or_404(Tueste, pk=pk)
    detalle = get_object_or_404(DetalleTueste, pk=detalle_pk, tueste=tueste)

    if request.method == 'POST':
        form = BatchTuesteForm(request.POST, instance=detalle)
        if form.is_valid():
            detalle = form.save(commit=False)
            detalle.tueste = tueste
            detalle.save()
            recalcular_totales_tueste_desde_batches(tueste)
            tueste.refresh_from_db()
            if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
                return respuesta_guardado_batch_en_modal_padre(request, tueste)
            return respuesta_guardado_batch(request)
    else:
        form = BatchTuesteForm(instance=detalle)

    return render(request, 'tueste/batch_OrdenesTueste.html', {
        'form': form,
        'tueste': tueste,
        'detalle': detalle,
        'numero_batch': detalle.numero_batch,
    })


@permiso_accion_requerido('tueste.delete_tueste', 'eliminar_orden_tueste')
def delete_orden_tueste(request, pk):
    t = get_object_or_404(Tueste, pk=pk)
    if request.method == 'POST':
        t.delete()
        if request.headers.get('X-Fragment'):
            return listar_ordenes_tueste(request)
        return redirect('ordenes_tueste_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'tueste/confirm_delete_OrdenesTueste.html', {'t': t})
    return render(request, 'tueste/listar_OrdenesTueste.html', {})
