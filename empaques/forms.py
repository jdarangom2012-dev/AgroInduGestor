from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from cafe_empaque.models import CafeEmpaque
from clientes.models import Cliente
from estado_tareas.models import EstadoTarea
from nivel_molienda.models import NivelMolienda
from ordenes.forms import enforce_parent_order_not_completed
from ordenes.models import Orden
from tamano_empaque.models import TamanoEmpaque

from .models import DetalleEmpaque, Empaque


COMPLETADA_PESOS_ERROR = 'La tarea no se puede poner en estado completada porque uno o más pesos son menores o iguales a cero.'


def estado_tareas_es_completada(estado_tareas):
    estado_nombre = (getattr(estado_tareas, 'estado_tareas', '') or '').strip().lower()
    return estado_nombre == 'completada'


class OrdenChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return str(obj)


class OrdenClienteSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        instance = getattr(value, 'instance', None)
        cliente_id = getattr(instance, 'cliente_id', None)
        if cliente_id is not None:
            option['attrs']['data-cliente-id'] = str(cliente_id)
        trabajo_empaque = bool(getattr(instance, 'trabajo_empaque', False))
        option['attrs']['data-trabajo-empaque'] = '1' if trabajo_empaque else '0'
        return option


class EmpaqueForm(forms.ModelForm):
    orden = OrdenChoiceField(
        queryset=Orden.objects.none(),
        required=False,
        widget=OrdenClienteSelect(
            attrs={
                'class': 'w-full select',
                'data-cliente-target': 'id_cliente',
                'onchange': "(function(select){const form=select.form||select.closest('form');if(!form)return;const target=form.querySelector('#'+(select.dataset.clienteTarget||'id_cliente'));if(!target)return;const option=select.options[select.selectedIndex];const clienteId=option?option.getAttribute('data-cliente-id'):'';target.value=clienteId||'';})(this)",
            }
        ),
    )
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(),
        required=False,
        disabled=True,
        widget=forms.Select(attrs={'class': 'w-full select'})
    )
    CANT_ETIQUETAS_REQUERIDA_ERROR = 'Debe ingresar una Cantidad de Etiquetas mayor a cero porque la opción Lleva Etiquetas está seleccionada.'

    class Meta:
        model = Empaque
        fields = ['orden', 'estado_tareas', 'lleva_etiquetas', 'cant_etiquetas', 'emp_clientes', 'cant_empacada', 'total_paquetes', 'notas']
        widgets = {
            'estado_tareas': forms.Select(attrs={'class': 'w-full select'}),
            'lleva_etiquetas': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border-brand-dark/30 text-brand-primary focus:ring-brand-primary/70',
                'onchange': "(function(checkbox){const form=checkbox.form||checkbox.closest('form');if(!form)return;const target=form.querySelector('[name=cant_etiquetas]');if(!target)return;target.disabled=!checkbox.checked;if(!checkbox.checked){target.value='';}})(this)",
            }),
            'cant_etiquetas': forms.NumberInput(attrs={'class': 'w-full input', 'min': '0', 'step': '1'}),
            'emp_clientes': forms.NumberInput(attrs={'class': 'w-full input', 'min': '0', 'step': '1'}),
            'cant_empacada': forms.NumberInput(attrs={'class': 'w-full input', 'min': '0', 'step': '1', 'readonly': 'readonly'}),
            'total_paquetes': forms.NumberInput(attrs={'class': 'w-full input', 'min': '0', 'step': '1'}),
            'notas': forms.Textarea(attrs={'class': 'w-full textarea', 'rows': '3', 'maxlength': '500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_qs = Orden.objects.filter(empaque_flag=True).order_by('-id')
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

        lleva_etiquetas = self.data.get('lleva_etiquetas') if self.is_bound else getattr(self.instance, 'lleva_etiquetas', False)
        if not bool(lleva_etiquetas):
            self.fields['cant_etiquetas'].widget.attrs['disabled'] = 'disabled'
        else:
            self.fields['cant_etiquetas'].widget.attrs.pop('disabled', None)

        valor_total_paquetes = getattr(self.instance, 'total_paquetes', None)
        if valor_total_paquetes is not None and not self.is_bound:
            self.fields['total_paquetes'].initial = valor_total_paquetes
            self.initial['total_paquetes'] = valor_total_paquetes

        self.fields['emp_clientes'].required = False
        self.fields['cant_empacada'].required = False
        self.fields['cant_empacada'].widget.attrs['readonly'] = 'readonly'

    def clean(self):
        cleaned = super().clean()
        if not enforce_parent_order_not_completed(self):
            return cleaned
        lleva_etiquetas = bool(cleaned.get('lleva_etiquetas'))
        cant_etiquetas = cleaned.get('cant_etiquetas')
        estado_tareas = cleaned.get('estado_tareas')
        estado_completada = estado_tareas_es_completada(estado_tareas)
        requiere_cant_etiquetas = bool(getattr(self.instance, 'pk', None)) and estado_completada and lleva_etiquetas

        if requiere_cant_etiquetas and (cant_etiquetas is None or cant_etiquetas <= 0):
            self.add_error('cant_etiquetas', self.CANT_ETIQUETAS_REQUERIDA_ERROR)

        if not estado_completada:
            return cleaned

        cantidades_requeridas = [cleaned.get('cant_empacada')]
        if requiere_cant_etiquetas and cant_etiquetas not in (None, '') and cant_etiquetas > 0:
            cantidades_requeridas.append(cant_etiquetas)

        if any(cantidad is None or cantidad <= 0 for cantidad in cantidades_requeridas):
            raise ValidationError(COMPLETADA_PESOS_ERROR)

        return cleaned


class DetalleEmpaqueForm(forms.ModelForm):
    require_positive_quantities = False

    class Meta:
        model = DetalleEmpaque
        fields = ['empaque_cafe', 'tamano_empaque', 'pedido', 'empacado', 'nivel_molienda', 'suministro', 'notas']
        widgets = {
            'empaque_cafe': forms.Select(attrs={'class': 'w-full select'}),
            'tamano_empaque': forms.Select(attrs={'class': 'w-full select'}),
            'pedido': forms.NumberInput(attrs={'class': 'w-full input', 'min': '0', 'step': '1', 'placeholder': '0'}),
            'empacado': forms.NumberInput(attrs={'class': 'w-full input', 'min': '0', 'step': '1', 'placeholder': '0'}),
            'nivel_molienda': forms.Select(attrs={'class': 'w-full select'}),
            'suministro': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-brand-dark/30 text-brand-primary focus:ring-brand-primary/70'}),
            'notas': forms.TextInput(attrs={'class': 'w-full input', 'maxlength': '255', 'placeholder': 'Notas'}),
        }

    def __init__(self, *args, **kwargs):
        self.require_positive_quantities = bool(kwargs.pop('require_positive_quantities', False))
        super().__init__(*args, **kwargs)
        self.fields['empaque_cafe'].queryset = CafeEmpaque.objects.all().order_by('empaque_cafe', 'id')
        self.fields['tamano_empaque'].queryset = TamanoEmpaque.objects.all().order_by('tamano_empaque', 'id')
        self.fields['nivel_molienda'].queryset = NivelMolienda.objects.all().order_by('nivel_molienda', 'id')

        self.fields['empaque_cafe'].empty_label = 'Seleccione...'
        self.fields['tamano_empaque'].empty_label = 'Seleccione...'
        self.fields['nivel_molienda'].empty_label = 'Seleccione...'

        for field_name in ['empaque_cafe', 'tamano_empaque', 'pedido', 'empacado', 'nivel_molienda', 'notas']:
            self.fields[field_name].required = False

    def clean(self):
        cleaned = super().clean()

        if cleaned.get('DELETE'):
            return cleaned

        empaque_cafe = cleaned.get('empaque_cafe')
        tamano_empaque = cleaned.get('tamano_empaque')
        pedido = cleaned.get('pedido')
        empacado = cleaned.get('empacado')
        nivel_molienda = cleaned.get('nivel_molienda')
        notas = (cleaned.get('notas') or '').strip()
        suministro = cleaned.get('suministro')

        has_any = any([
            empaque_cafe is not None,
            tamano_empaque is not None,
            pedido is not None,
            empacado is not None,
            nivel_molienda is not None,
            bool(suministro),
            bool(notas),
        ])

        if not has_any:
            return cleaned

        if empaque_cafe is None:
            self.add_error('empaque_cafe', 'Seleccione un Empaque Café.')

        if tamano_empaque is None:
            self.add_error('tamano_empaque', 'Seleccione un Tamaño Empaque.')

        if self.require_positive_quantities:
            if pedido in (None, '') or pedido <= 0:
                self.add_error('pedido', 'Debe ingresar el pedido.')

            if empacado in (None, '') or empacado <= 0:
                self.add_error('empacado', 'Debe ingresar lo empacado.')

        if nivel_molienda is None:
            self.add_error('nivel_molienda', 'Seleccione la molienda.')

        return cleaned


class BaseDetalleEmpaqueFormSet(BaseInlineFormSet):
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['require_positive_quantities'] = bool(getattr(self.instance, 'pk', None))
        return kwargs

    def _estado_tareas_actual(self):
        if self.is_bound:
            estado_tareas_id = self.data.get('estado_tareas')
            if estado_tareas_id not in (None, ''):
                try:
                    return EstadoTarea.objects.only('estado_tareas').get(pk=estado_tareas_id)
                except (TypeError, ValueError, EstadoTarea.DoesNotExist):
                    return None
        return getattr(self.instance, 'estado_tareas', None)

    def clean(self):
        super().clean()

        filas_activas = 0

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue

            cleaned = form.cleaned_data
            if cleaned.get('DELETE'):
                continue

            has_any = any([
                cleaned.get('empaque_cafe') is not None,
                cleaned.get('tamano_empaque') is not None,
                cleaned.get('pedido') is not None,
                cleaned.get('empacado') is not None,
                cleaned.get('nivel_molienda') is not None,
                bool(cleaned.get('suministro')),
                bool((cleaned.get('notas') or '').strip()),
            ])

            if has_any:
                filas_activas += 1

        permitir_vacio_legacy = bool(getattr(self.instance, 'pk', None)) and self.initial_form_count() == 0
        if filas_activas == 0 and not permitir_vacio_legacy:
            raise ValidationError('Debe registrar al menos una linea de empaque.')

        if not getattr(self.instance, 'pk', None):
            return

        if not estado_tareas_es_completada(self._estado_tareas_actual()):
            return

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue

            cleaned = form.cleaned_data
            if cleaned.get('DELETE'):
                continue

            has_any = any([
                cleaned.get('empaque_cafe') is not None,
                cleaned.get('tamano_empaque') is not None,
                cleaned.get('pedido') is not None,
                cleaned.get('empacado') is not None,
                cleaned.get('nivel_molienda') is not None,
                bool(cleaned.get('suministro')),
                bool((cleaned.get('notas') or '').strip()),
            ])

            if not has_any:
                continue

            cantidades_requeridas = (
                cleaned.get('pedido'),
                cleaned.get('empacado'),
            )
            if any(cantidad is None or cantidad <= 0 for cantidad in cantidades_requeridas):
                raise ValidationError(COMPLETADA_PESOS_ERROR)


DetalleEmpaqueFormSet = inlineformset_factory(
    Empaque,
    DetalleEmpaque,
    form=DetalleEmpaqueForm,
    formset=BaseDetalleEmpaqueFormSet,
    extra=1,
    can_delete=True,
)


def build_detalle_empaque_formset(*, data=None, instance=None):
    if instance is None:
        instance = Empaque()
    if data is not None and 'detalle_empaque-TOTAL_FORMS' not in data:
        data = None
    return DetalleEmpaqueFormSet(data=data, instance=instance, prefix='detalle_empaque')
