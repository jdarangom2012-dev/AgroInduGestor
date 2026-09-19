import json

from django import forms
from django.core.validators import MinValueValidator

from clientes.models import Cliente
from proceso_inven_cafe.models import ProcesoInvenCafe

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

    class Meta:
        model = Calidad
        fields = [
            'cliente', 'fecha_recibido', 'sencilla', 'q_grader', 'muestra_numero',
            'orden', 'variedad', 'proceso', 'origen', 'altura', 'peso_pergamino',
            'humedad', 'densidad', 'peso_verde', 'peso_excelsio', 'factor',
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
        for name in ('orden', 'muestra_numero', 'variedad', 'origen'):
            self.fields[name].widget.attrs.update({'class': 'w-full input'})
        for name in ('altura', 'peso_pergamino', 'humedad', 'densidad', 'peso_verde', 'peso_excelsio', 'factor', 'peso_tostado'):
            self.fields[name].widget.attrs.update({'class': 'w-full input', 'step': 'any', 'min': '0'})
            self.fields[name].validators.append(MinValueValidator(0))

        lecturas = {item.get('tiempo'): item for item in self.instance.lecturas_tostion}
        self.tostion_filas = []
        for indice, tiempo in enumerate(TIEMPOS_TOSTION):
            temperatura_nombre = f'temperatura_{indice}'
            evento_nombre = f'evento_{indice}'
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
            self.tostion_filas.append((tiempo, self[temperatura_nombre], self[evento_nombre]))

    def clean_orden(self):
        return (self.cleaned_data['orden'] or '').strip()

    def save(self, commit=True):
        instancia = super().save(commit=False)
        lecturas = []
        for indice, tiempo in enumerate(TIEMPOS_TOSTION):
            temperatura = self.cleaned_data.get(f'temperatura_{indice}')
            evento = (self.cleaned_data.get(f'evento_{indice}') or '').strip()
            if temperatura is not None or evento:
                lecturas.append({'tiempo': tiempo, 'temperatura': temperatura, 'evento': evento})
        instancia.tostion_json = json.dumps(lecturas, ensure_ascii=False)
        if commit:
            instancia.save()
        return instancia
