import json

from django import forms
from django.core.validators import MinValueValidator

from clientes.models import Cliente
from origen_cafe.models import OrigenCafe
from proceso_inven_cafe.models import ProcesoInvenCafe
from variedad_cafe.models import VariedadCafe

from .models import Calidad


TIEMPOS_TOSTION = tuple(f'{minutos}:{segundos:02d}' for minutos in range(10) for segundos in (0, 30))


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
