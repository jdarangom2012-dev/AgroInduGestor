from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from seguridad.decorators import permiso_accion_requerido
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django import forms
from django.conf import settings
import re
from .models import OrdenTrilla
from ordenes.models import Orden
from ordenes.forms import enforce_parent_order_not_completed
from estado_tareas.models import EstadoTarea
from clientes.models import Cliente
from seguridad.helpers import puede_editar_campo
from seguridad.models import PermisoCampo

COMPLETADA_PESOS_ERROR = 'No es posible completar la Orden de Trilla. Los campos Peso Café Neto y Peso Café Verde deben ser mayores a cero.'


def estado_tareas_es_completada(estado_tareas):
    estado_nombre = (getattr(estado_tareas, 'estado_tareas', '') or '').strip().lower()
    return estado_nombre == 'completada'


def pesos_completan_trilla(peso_cafe_neto, peso_cafe_verde):
    return (
        peso_cafe_neto is not None
        and peso_cafe_verde is not None
        and peso_cafe_neto > 0
        and peso_cafe_verde > 0
    )


class OrdenChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return str(obj)


def _calcular_rendimiento(peso_cafe_neto, peso_cafe_verde):
    try:
        neto = float(peso_cafe_neto)
    except (TypeError, ValueError):
        neto = 0.0

    try:
        verde = float(peso_cafe_verde)
    except (TypeError, ValueError):
        verde = 0.0

    if not verde or verde == 0:
        return 0.0

    return round((neto / verde) * 100.0, 2)


class OrdenTrillaForm(forms.ModelForm):
    # Campos adicionales (no guardados por el ModelForm) para mostrar y enviar al backend
    fecha_ingreso = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'type': 'date', 'class': 'input-form w-full input', 'data-datepicker': '1'},
        ),
    )
    orden = OrdenChoiceField(queryset=Orden.objects.none(), required=False, widget=forms.Select(attrs={'class':'w-full select'}))
    estado_tareas = forms.ModelChoiceField(queryset=EstadoTarea.objects.all().order_by('estado_tareas'), required=False, widget=forms.Select(attrs={'class':'w-full select'}))

    class Meta:
        model = OrdenTrilla
        # fecha_ingreso es automática; no se expone en el formulario
        fields = ['cliente', 'orden','estado_tareas','peso_cafe_bruto','peso_cafe_verde','rendimiento', 'notas']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'w-full select'}),
            'peso_cafe_bruto': forms.NumberInput(attrs={'class':'w-full input', 'step':'0.01'}),
            'peso_cafe_verde': forms.NumberInput(attrs={'class':'w-full input', 'step':'0.01'}),
            'rendimiento': forms.NumberInput(attrs={'class':'w-full input', 'step':'0.01', 'readonly': 'readonly'}),
            'notas': forms.Textarea(attrs={'class':'w-full input', 'rows':'3', 'maxlength':'500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Órdenes: cuando está ligado (POST), permitir cualquier orden para evitar errores de validación
        base_qs = Orden.objects.all().order_by('-id')
        if self.is_bound:
            # Evita "Escoja una opción válida" aunque la orden no esté en el top N
            self.fields['orden'].queryset = base_qs
        else:
            # En carga inicial, limitar para rendimiento
            self.fields['orden'].queryset = base_qs.select_related('cliente')[:200]
        self.fields['orden'].empty_label = 'Seleccione una orden'
        # Inicializar valores para campos adicionales cuando hay una instancia
        inst = kwargs.get('instance', None)
        if inst:
            try:
                if hasattr(inst, 'fecha_ingreso') and inst.fecha_ingreso:
                    # asignar fecha (solo fecha, sin hora)
                    self.fields['fecha_ingreso'].initial = inst.fecha_ingreso.date()
            except Exception:
                pass
            try:
                # Inicial: si la trilla ya tiene cliente directo úsalo; si no, intenta desde la orden.
                if getattr(inst, 'cliente_id', None):
                    self.fields['cliente'].initial = inst.cliente_id
                elif getattr(inst, 'orden', None) and getattr(inst.orden, 'cliente', None):
                    self.fields['cliente'].initial = inst.orden.cliente.pk
            except Exception:
                pass

    def clean(self):
        cleaned_data = super().clean()
        if not enforce_parent_order_not_completed(self):
            return cleaned_data
        peso_cafe_verde = cleaned_data.get('peso_cafe_verde')
        peso_cafe_neto = cleaned_data.get('peso_cafe_bruto')
        estado_tareas = cleaned_data.get('estado_tareas')

        if estado_tareas_es_completada(estado_tareas):
            if not pesos_completan_trilla(peso_cafe_neto, peso_cafe_verde):
                raise forms.ValidationError(COMPLETADA_PESOS_ERROR)

        rendimiento = _calcular_rendimiento(peso_cafe_neto, peso_cafe_verde)
        cleaned_data['rendimiento'] = rendimiento
        return cleaned_data


def _build_orden_trilla_defaults(orden):
    cliente = getattr(orden, 'cliente', None)
    estado_pendiente = EstadoTarea.objects.filter(estado_tareas__iexact='Pendiente').order_by('id').first()

    return {
        'cliente_id': getattr(cliente, 'id', None),
        'cliente_label': str(cliente) if cliente is not None else '',
        'peso_cafe_bruto': getattr(orden, 'peso', None),
        'estado_tareas_id': getattr(estado_pendiente, 'id', None),
        'estado_tareas_label': getattr(estado_pendiente, 'estado_tareas', '') if estado_pendiente is not None else '',
    }


@require_http_methods(["GET"])
@permiso_accion_requerido('ordenes_trilla.add_ordentrilla', 'crear_orden_trilla')
def orden_trilla_defaults(request):
    orden_id = request.GET.get('orden_id')
    if not orden_id:
        return JsonResponse(_build_orden_trilla_defaults(Orden()))

    try:
        orden = Orden.objects.select_related('cliente').get(pk=orden_id)
    except (TypeError, ValueError, Orden.DoesNotExist):
        return JsonResponse({'detail': 'Orden no encontrada.'}, status=404)

    return JsonResponse(_build_orden_trilla_defaults(orden))


@permiso_accion_requerido('ordenes_trilla.view_ordentrilla', 'ver_orden_trilla')
def listar_ordenes_trilla(request):
    qs = OrdenTrilla.objects.select_related('cliente', 'orden__cliente','estado_tareas')
    search = request.GET.get('q','').strip()
    if search:
        s = search.strip()
        filters = (
            Q(orden__cliente__nombre__icontains=s) |
            Q(orden__cliente__apellidos__icontains=s)
        )
        # Soportar texto completo como "Orden 6" o el número aislado "6"
        m = re.search(r"(?:^|\b)orden\s*(\d+)\b", s, flags=re.IGNORECASE)
        if m:
            try:
                filters |= Q(orden__id=int(m.group(1)))
            except ValueError:
                pass
        else:
            # Si no hay patrón "Orden N", pero hay un número en el término, úsalo
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

    ctx = {
        'trillas': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'search': search,
    }

    # Robustez: si existe IdClientes huérfano, acceder a orden.cliente puede lanzar Cliente.DoesNotExist.
    # Guardamos un display seguro por fila para que el template no reviente.
    for t in page_obj:
        display = '—'
        # Prioridad: cliente directo en OrdenTrilla; fallback: cliente de la orden.
        if getattr(t, 'cliente_id', None):
            try:
                display = str(t.cliente) if t.cliente else '—'
            except Cliente.DoesNotExist:
                display = 'Sin cliente'
        elif getattr(t, 'orden_id', None):
            try:
                c = t.orden.cliente  # puede lanzar Cliente.DoesNotExist
                display = str(c) if c else '—'
            except Cliente.DoesNotExist:
                display = 'Sin cliente'
        setattr(t, 'cliente_display', display)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'ordenes_trilla/_modal_listar_OrdenesTrilla.html', ctx)
    return render(request, 'ordenes_trilla/listar_OrdenesTrilla.html', ctx)


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('ordenes_trilla.add_ordentrilla', 'crear_orden_trilla')
def add_orden_trilla(request):
    if request.method == 'POST':
        if settings.DEBUG:
            print("POST DATA:", request.POST)
        form = OrdenTrillaForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            # Compatibilidad progresiva: si no se especifica cliente, intentar tomarlo desde la orden.
            if not getattr(obj, 'cliente_id', None) and getattr(obj, 'orden', None):
                try:
                    if getattr(obj.orden, 'cliente_id', None):
                        obj.cliente = obj.orden.cliente
                except Cliente.DoesNotExist:
                    pass
            # Compatibilidad: mantener Orden.cliente sincronizado cuando se seleccione cliente en Trilla.
            if getattr(obj, 'cliente_id', None) and getattr(obj, 'orden', None):
                orden = obj.orden
                if orden and getattr(orden, 'cliente_id', None) != obj.cliente_id:
                    orden.cliente_id = obj.cliente_id
                    orden.save(update_fields=['cliente'])
            from django.utils import timezone
            # Fecha de ingreso automática
            obj.rendimiento = _calcular_rendimiento(obj.peso_cafe_bruto, obj.peso_cafe_verde)
            obj.fecha_ingreso = timezone.now()
            obj.created_at = timezone.now()
            obj.updated_at = timezone.now()
            obj.save()
            if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                return listar_ordenes_trilla(request)
            return redirect('ordenes_trilla_listar')
    else:
        form = OrdenTrillaForm()
    # Siempre mostrar el formulario, tanto por AJAX, fragment o acceso directo
    return render(request, 'ordenes_trilla/add_OrdenesTrilla.html', {'form': form})


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('ordenes_trilla.change_ordentrilla', 'editar_orden_trilla')
def edit_orden_trilla(request, pk):
    trilla = get_object_or_404(OrdenTrilla, pk=pk)

    # Display seguro del cliente actual (evita Cliente.DoesNotExist si hay FK huérfano)
    cliente_display = ''
    if getattr(trilla, 'cliente_id', None):
        try:
            cliente_display = str(trilla.cliente) if trilla.cliente else ''
        except Cliente.DoesNotExist:
            cliente_display = 'Sin cliente'
    elif getattr(trilla, 'orden_id', None):
        try:
            c = trilla.orden.cliente
            cliente_display = str(c) if c else ''
        except Cliente.DoesNotExist:
            cliente_display = 'Sin cliente'

    modelo_perm = 'OrdenTrilla'
    campos_perm = [
        'fecha_ingreso',
        'cliente',
        'orden',
        'estado_tareas',
        'peso_cafe_bruto',
        'peso_cafe_verde',
        'rendimiento',
        'notas',
    ]
    configurados = set(
        PermisoCampo.objects.filter(modelo=modelo_perm, campo__in=campos_perm)
        .values_list('campo', flat=True)
        .distinct()
    )

    def _can_edit(campo: str) -> bool:
        # Compatibilidad: si no hay configuración para el campo, mantener el comportamiento histórico (editable).
        if getattr(request.user, 'is_superuser', False):
            return True
        if campo not in configurados:
            return True
        return bool(puede_editar_campo(request.user, modelo_perm, campo))

    can_edit = {c: _can_edit(c) for c in campos_perm}

    if request.method == 'POST':
        if settings.DEBUG:
            print("POST DATA:", request.POST)
        form = OrdenTrillaForm(request.POST, instance=trilla)
        if form.is_valid():
            if not enforce_parent_order_not_completed(form):
                return render(request, 'ordenes_trilla/detail_OrdenesTrilla.html', {'form': form, 'trilla': trilla, 'cliente_display': cliente_display, 'can_edit': can_edit})
            obj = form.save(commit=False)

            # Seguridad backend: si no hay permiso, mantener el valor original
            if not can_edit.get('orden', True):
                obj.orden = trilla.orden
            if not can_edit.get('estado_tareas', True):
                obj.estado_tareas = trilla.estado_tareas
            if not can_edit.get('cliente', True):
                obj.cliente = trilla.cliente
            if not can_edit.get('peso_cafe_bruto', True):
                obj.peso_cafe_bruto = trilla.peso_cafe_bruto
            if not can_edit.get('peso_cafe_verde', True):
                obj.peso_cafe_verde = trilla.peso_cafe_verde
            if not can_edit.get('rendimiento', True):
                obj.rendimiento = trilla.rendimiento
            if not can_edit.get('notas', True):
                obj.notas = trilla.notas

            # Compatibilidad progresiva: si cliente queda vacío, intentar tomarlo desde la orden.
            if can_edit.get('cliente', True) and not getattr(obj, 'cliente_id', None) and getattr(obj, 'orden', None):
                try:
                    if getattr(obj.orden, 'cliente_id', None):
                        obj.cliente = obj.orden.cliente
                except Cliente.DoesNotExist:
                    pass

            # Compatibilidad: mantener Orden.cliente sincronizado cuando se edite cliente en Trilla.
            if can_edit.get('cliente', True) and getattr(obj, 'cliente_id', None) and getattr(obj, 'orden', None):
                orden = obj.orden
                if orden and getattr(orden, 'cliente_id', None) != obj.cliente_id:
                    orden.cliente_id = obj.cliente_id
                    orden.save(update_fields=['cliente'])

            from django.utils import timezone
            obj.rendimiento = _calcular_rendimiento(obj.peso_cafe_bruto, obj.peso_cafe_verde)
            obj.updated_at = timezone.now()
            obj.save()
            if request.headers.get('X-Fragment'):
                return listar_ordenes_trilla(request)
            return redirect('ordenes_trilla_listar')
    else:
        form = OrdenTrillaForm(instance=trilla)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(
            request,
            'ordenes_trilla/detail_OrdenesTrilla.html',
            {
                'form': form,
                'trilla': trilla,
                'can_edit': can_edit,
                'cliente_display': cliente_display,
            },
        )
    return render(request, 'ordenes_trilla/listar_OrdenesTrilla.html', {})


@permiso_accion_requerido('ordenes_trilla.delete_ordentrilla', 'eliminar_orden_trilla')
def delete_orden_trilla(request, pk):
    t = get_object_or_404(OrdenTrilla, pk=pk)
    if request.method == 'POST':
        t.delete()
        if request.headers.get('X-Fragment'):
            return listar_ordenes_trilla(request)
        return redirect('ordenes_trilla_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'ordenes_trilla/confirm_delete_OrdenesTrilla.html', {'t': t})
    return render(request, 'ordenes_trilla/listar_OrdenesTrilla.html', {})
