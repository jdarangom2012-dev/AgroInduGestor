import json

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone

from clientes.models import Cliente
from origen_cafe.models import OrigenCafe
from proceso_inven_cafe.models import ProcesoInvenCafe
from variedad_cafe.models import VariedadCafe

from .models import AnalisisSensorial, Calidad


class RangeInput(forms.NumberInput):
    input_type = 'range'


TIEMPOS_TOSTION = tuple(f'{minutos}:{segundos:02d}' for minutos in range(10) for segundos in (0, 30))

DESCRIPTORES_SENSORIALES = (
    ('floral', 'Floral'), ('afrutado', 'Afrutado'), ('bayas', 'Bayas'),
    ('frutas_deshidratadas', 'Frutas deshidratadas'), ('citricos', 'Cítricos'),
    ('acido_fermentado', 'Ácido/Fermentado'), ('acido', 'Ácido'), ('fermentado', 'Fermentado'),
    ('verde_vegetal', 'Verde/Vegetal'), ('otra', 'Otra'), ('quimico', 'Químico'),
    ('humedad_tierra', 'Humedad/Tierra'), ('madera', 'Madera'), ('tostado', 'Tostado'),
    ('cereal', 'Cereal'), ('quemado', 'Quemado'), ('tabaco', 'Tabaco'),
    ('nueces_cacao', 'Nueces/Cacao'), ('nueces', 'Nueces'), ('cacao', 'Cacao'),
    ('especias', 'Especias'), ('dulce', 'Dulce'), ('vainilla', 'Vainilla'),
    ('azucar_morena', 'Azúcar morena'),
)
GUSTOS_PREDOMINANTES = (
    ('salado', 'Salado'), ('acido', 'Ácido'), ('dulce', 'Dulce'),
    ('amargo', 'Amargo'), ('umami', 'Umami'),
)
SENSACIONES_BOCA = (
    ('aspero', 'Áspero (Arenoso, Rugoso, Rasposo)'), ('aceitoso', 'Aceitoso'),
    ('suave', 'Suave (Aterciopelado, Sedoso, Almibarado)'),
    ('astringente', 'Deja seca la boca (astringente)'), ('metalico', 'Metálico'),
)
DEFECTOS_HABERLO = (('mohoso', 'Mohoso'), ('fenolico', 'Fenólico'), ('papa', 'Papa'))


class CalidadForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all().order_by('nombre', 'apellidos'),
        widget=forms.Select(attrs={'class': 'w-full select'}),
    )
    proceso = forms.ModelChoiceField(
        queryset=ProcesoInvenCafe.objects.all().order_by('proceso_inven_cafe'),
        widget=forms.Select(attrs={'class': 'w-full select'}),
    )
    variedad = forms.ChoiceField(
        required=False,
        choices=(),
        widget=forms.Select(attrs={'class': 'w-full select'}),
    )
    origen = forms.ChoiceField(
        required=False,
        choices=(),
        widget=forms.Select(attrs={'class': 'w-full select'}),
    )

    class Meta:
        model = Calidad
        fields = [
            'cliente', 'fecha_recibido', 'sencilla', 'q_grader', 'muestra_numero',
            'orden', 'variedad', 'proceso', 'origen', 'altura', 'peso_pergamino',
            'humedad', 'densidad', 'peso_verde', 'peso_excelsio', 'peso_defecto', 'factor',
            'notas', 'peso_tostado', 'observaciones',
        ]
        widgets = {
            'fecha_recibido': forms.DateInput(attrs={'class': 'w-full input', 'type': 'date'}, format='%Y-%m-%d'),
            'notas': forms.Textarea(attrs={'class': 'w-full textarea', 'rows': 3}),
            'observaciones': forms.Textarea(attrs={'class': 'w-full textarea', 'rows': 3}),
            'sencilla': forms.CheckboxInput(attrs={'class': 'checkbox'}),
            'q_grader': forms.CheckboxInput(attrs={'class': 'checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].empty_label = 'Seleccione un cliente…'
        self.fields['proceso'].empty_label = 'Seleccione un proceso…'
        self.fields['variedad'].choices = self._opciones_maestro(
            VariedadCafe.objects.order_by('variedad_cafe', 'id').values_list('variedad_cafe', flat=True),
            'Seleccione una variedad…',
            self.instance.variedad,
        )
        self.fields['origen'].choices = self._opciones_maestro(
            OrigenCafe.objects.order_by('origen', 'id').values_list('origen', flat=True),
            'Seleccione un origen…',
            self.instance.origen,
        )
        for name in ('orden', 'muestra_numero'):
            self.fields[name].widget.attrs.update({'class': 'w-full input'})
        for name in ('altura', 'peso_pergamino', 'humedad', 'densidad', 'peso_verde', 'peso_excelsio', 'peso_defecto', 'factor', 'peso_tostado'):
            self.fields[name].widget.attrs.update({'class': 'w-full input', 'step': 'any', 'min': '0'})
            self.fields[name].validators.append(MinValueValidator(0))

        lecturas = {item.get('tiempo'): item for item in self.instance.lecturas_tostion}
        self.tostion_filas = []
        for indice, tiempo in enumerate(TIEMPOS_TOSTION):
            temperatura_nombre = f'temperatura_{indice}'
            evento_nombre = f'evento_{indice}'
            potencia_gas_nombre = f'potencia_gas_{indice}'
            potencia_aire_nombre = f'potencia_aire_{indice}'
            anterior = lecturas.get(tiempo, {})
            self.fields[temperatura_nombre] = forms.FloatField(
                required=False, min_value=0,
                initial=anterior.get('temperatura'),
                widget=forms.NumberInput(attrs={'class': 'w-full input', 'step': 'any', 'min': '0'}),
            )
            self.fields[evento_nombre] = forms.CharField(
                required=False, max_length=120,
                initial=anterior.get('evento', ''),
                widget=forms.TextInput(attrs={'class': 'w-full input'}),
            )
            self.fields[potencia_gas_nombre] = forms.IntegerField(
                required=False, min_value=0,
                initial=anterior.get('potencia_gas'),
                widget=forms.NumberInput(attrs={'class': 'w-full input', 'step': '1', 'min': '0'}),
            )
            self.fields[potencia_aire_nombre] = forms.IntegerField(
                required=False, min_value=0,
                initial=anterior.get('potencia_aire'),
                widget=forms.NumberInput(attrs={'class': 'w-full input', 'step': '1', 'min': '0'}),
            )
            self.tostion_filas.append((
                tiempo,
                self[temperatura_nombre],
                self[evento_nombre],
                self[potencia_gas_nombre],
                self[potencia_aire_nombre],
            ))

    @staticmethod
    def _opciones_maestro(valores, etiqueta_vacia, valor_historico=''):
        """Usa el texto del maestro sin alterar las columnas históricas de Calidad."""
        opciones = []
        vistos = set()
        for valor in valores:
            valor = (valor or '').strip()
            if valor and valor not in vistos:
                opciones.append((valor, valor))
                vistos.add(valor)

        valor_historico = (valor_historico or '').strip()
        if valor_historico and valor_historico not in vistos:
            opciones.append((valor_historico, f'{valor_historico} (valor histórico)'))

        return [('', etiqueta_vacia), *opciones]

    def clean_orden(self):
        return (self.cleaned_data['orden'] or '').strip()

    def save(self, commit=True):
        instancia = super().save(commit=False)
        lecturas = []
        for indice, tiempo in enumerate(TIEMPOS_TOSTION):
            temperatura = self.cleaned_data.get(f'temperatura_{indice}')
            evento = (self.cleaned_data.get(f'evento_{indice}') or '').strip()
            potencia_gas = self.cleaned_data.get(f'potencia_gas_{indice}')
            potencia_aire = self.cleaned_data.get(f'potencia_aire_{indice}')
            if temperatura is not None or evento or potencia_gas is not None or potencia_aire is not None:
                lecturas.append({
                    'tiempo': tiempo,
                    'temperatura': temperatura,
                    'evento': evento,
                    'potencia_gas': potencia_gas,
                    'potencia_aire': potencia_aire,
                })
        instancia.tostion_json = json.dumps(lecturas, ensure_ascii=False)
        if commit:
            instancia.save()
        return instancia


class AnalisisSensorialForm(forms.ModelForm):
    descriptores_fragancia_aroma = forms.MultipleChoiceField(
        required=False, choices=DESCRIPTORES_SENSORIALES,
        widget=forms.CheckboxSelectMultiple,
    )
    descriptores_sabor = forms.MultipleChoiceField(
        required=False, choices=DESCRIPTORES_SENSORIALES,
        widget=forms.CheckboxSelectMultiple,
    )
    gustos_predominantes = forms.MultipleChoiceField(
        required=False, choices=GUSTOS_PREDOMINANTES,
        widget=forms.CheckboxSelectMultiple,
    )
    sensaciones_boca = forms.MultipleChoiceField(
        required=False, choices=SENSACIONES_BOCA,
        widget=forms.CheckboxSelectMultiple,
    )
    defectos_haberlo = forms.MultipleChoiceField(
        required=False, choices=DEFECTOS_HABERLO,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = AnalisisSensorial
        fields = [
            'nombre', 'fecha', 'objetivo', 'muestra_numero', 'nivel_tueste',
            'intensidad_fragancia', 'intensidad_aroma', 'descriptores_fragancia_aroma',
            'notas_fragancia_aroma', 'intensidad_sabor', 'intensidad_sabor_residual',
            'descriptores_sabor', 'gustos_predominantes', 'notas_sabor',
            'intensidad_acidez', 'notas_acidez', 'intensidad_dulzor', 'notas_dulzor',
            'intensidad_sensacion_boca', 'sensaciones_boca', 'notas_sensacion_boca',
            'notas_extrinseca', 'calidad_fragancia', 'calidad_aroma',
            'notas_afectiva_fragancia_aroma', 'calidad_sabor', 'calidad_sabor_residual',
            'notas_afectiva_sabor', 'calidad_acidez', 'notas_afectiva_acidez',
            'calidad_dulzor', 'notas_afectiva_dulzor', 'calidad_sensacion_boca',
            'notas_afectiva_sensacion_boca', 'impresion_global', 'notas_impresion_global',
            'puntaje_total', 'tazas_no_uniformes', 'tazas_defectuosas', 'defectos_haberlo',
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'w-full input', 'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        campos_texto = ('nombre', 'objetivo', 'muestra_numero')
        campos_intensidad = (
            'intensidad_fragancia', 'intensidad_aroma', 'intensidad_sabor',
            'intensidad_sabor_residual', 'intensidad_acidez', 'intensidad_dulzor',
            'intensidad_sensacion_boca',
        )
        campos_calidad = (
            'calidad_fragancia', 'calidad_aroma', 'calidad_sabor', 'calidad_sabor_residual',
            'calidad_acidez', 'calidad_dulzor', 'calidad_sensacion_boca', 'impresion_global',
        )
        campos_notas = tuple(nombre for nombre in self.fields if nombre.startswith('notas_'))

        for nombre in campos_texto:
            self.fields[nombre].widget.attrs.update({'class': 'w-full input'})
        if not self.is_bound and not getattr(self.instance, 'pk', None):
            self.fields['fecha'].initial = timezone.localdate
        self.fields['nivel_tueste'].widget.attrs.update({'class': 'w-full input', 'min': '0', 'max': '15', 'step': '1'})
        self.fields['nivel_tueste'].validators.extend([MinValueValidator(0), MaxValueValidator(15)])
        for nombre in campos_intensidad:
            valor_inicial = self.fields[nombre].initial
            self.fields[nombre].widget = RangeInput(attrs={
                'class': 'sensory-heatmap w-full',
                'min': '0',
                'max': '15',
                'step': '0.5',
                'data-sensory-heatmap': 'true',
            })
            self.fields[nombre].initial = 0 if valor_inicial in (None, '') else valor_inicial
            self.fields[nombre].validators.extend([MinValueValidator(0), MaxValueValidator(15)])
        for nombre in campos_calidad:
            self.fields[nombre].widget = forms.Select(
                choices=[('', 'Seleccione...'), *((valor, str(valor)) for valor in range(1, 10))],
                attrs={'class': 'w-full select'},
            )
            self.fields[nombre].validators.extend([MinValueValidator(1), MaxValueValidator(9)])
        for nombre in campos_notas:
            self.fields[nombre].widget.attrs.update({'class': 'w-full textarea', 'rows': 3})
        self.fields['puntaje_total'].widget.attrs.update({'class': 'w-full input', 'min': '0', 'step': '0.01'})
        self.fields['puntaje_total'].validators.append(MinValueValidator(0))
        for nombre in ('tazas_no_uniformes', 'tazas_defectuosas'):
            self.fields[nombre].widget.attrs.update({'class': 'w-full input', 'min': '0', 'max': '5', 'step': '1'})
            self.fields[nombre].validators.extend([MinValueValidator(0), MaxValueValidator(5)])

        if self.instance and self.instance.pk:
            self.initial.update({
                'descriptores_fragancia_aroma': self.instance.lista_descriptores_fragancia_aroma,
                'descriptores_sabor': self.instance.lista_descriptores_sabor,
                'gustos_predominantes': self.instance.lista_gustos_predominantes,
                'sensaciones_boca': self.instance.lista_sensaciones_boca,
                'defectos_haberlo': self.instance.lista_defectos_haberlo,
            })

    def clean_gustos_predominantes(self):
        valores = self.cleaned_data.get('gustos_predominantes', [])
        if len(valores) > 2:
            raise forms.ValidationError('Selecciona máximo dos gustos predominantes.')
        return valores

    def save(self, commit=True):
        instancia = super().save(commit=False)
        for nombre in (
            'descriptores_fragancia_aroma', 'descriptores_sabor', 'gustos_predominantes',
            'sensaciones_boca', 'defectos_haberlo',
        ):
            setattr(instancia, nombre, json.dumps(self.cleaned_data.get(nombre, []), ensure_ascii=False))
        if commit:
            instancia.save()
        return instancia
