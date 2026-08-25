from django.shortcuts import render, get_object_or_404, redirect
from seguridad.decorators import permiso_accion_requerido
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Cliente
from django import forms
from django.db import IntegrityError


class ClienteForm(forms.ModelForm):
    def clean_codigo(self):
        # En edición, el código no debe poder cambiarse. Conservamos el valor
        # original del registro aunque el usuario intente manipular el POST.
        if self.instance and getattr(self.instance, 'pk', None):
            return self.instance.codigo

        codigo = self.cleaned_data.get('codigo')
        if codigo is None:
            return codigo
        codigo = codigo.strip()
        if codigo == '':
            return codigo

        qs = Cliente.objects.filter(codigo=codigo)
        if self.instance and getattr(self.instance, 'pk', None):
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('El código ya existe')

        return codigo

    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        # Validación estándar de email usando el validador de Django
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(email)
        except ValidationError:
            raise forms.ValidationError('Ingrese un email válido.')
        return email
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bloquear edición del código cuando se está editando un registro.
        # Usamos readonly (no disabled) para que el valor viaje en el POST.
        if self.instance and getattr(self.instance, 'pk', None):
            self.fields['codigo'].widget.attrs['readonly'] = True
            self.fields['codigo'].widget.attrs['aria-readonly'] = 'true'
            # En edición, tipo de cliente y tipo de identificación no son modificables.
            self.fields['id_tipo_cliente'].disabled = True
            self.fields['id_tipo_identificacion'].disabled = True

        # Si el instance o datos indican Empresa, marcar Apellidos como solo lectura en el render
        tipo_obj = None
        if self.instance and getattr(self.instance, 'id_tipo_cliente_id', None):
            tipo_obj = getattr(self.instance, 'id_tipo_cliente', None)
        else:
            # Si viene en POST, intentar usar el valor enviado para preconfigurar
            data = args[0] if args else None
            if isinstance(data, dict):
                # No resolvemos a objeto aquí; el JS del frontend lo gestionará dinámicamente
                pass
        if tipo_obj is not None:
            nombre_tipo = (getattr(tipo_obj, 'tipo_cliente', '') or '').strip().lower()
            if 'empresa' in nombre_tipo:
                # Para Empresa: desactivar apellidos, activar representante_legal
                self.fields['apellidos'].widget.attrs['readonly'] = True
                self.fields['apellidos'].widget.attrs['disabled'] = True
            else:
                # Para Persona Natural: activar apellidos, desactivar representante_legal
                self.fields['representante_legal'].widget.attrs['readonly'] = True
                self.fields['representante_legal'].widget.attrs['disabled'] = True

    class Meta:
        model = Cliente
        fields = '__all__'
        labels = {
            'codigo': 'Nro. de Identificación',
        }
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'w-full input'}),
            'nombre': forms.TextInput(attrs={'class': 'w-full input'}),
            'apellidos': forms.TextInput(attrs={'class': 'w-full input'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full input'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full input'}),
            'email': forms.EmailInput(attrs={'class': 'w-full input'}),
            'representante_legal': forms.TextInput(attrs={'class': 'w-full input'}),
            'id_tipo_cliente': forms.Select(attrs={'class': 'w-full select',
                                                  'onchange': "(function(s){var r=s.closest('[data-modal-root]')||document;var a=r.querySelector('[name=apellidos]');var rl=r.querySelector('[name=representante_legal]');var t=(s.options[s.selectedIndex].text||'').toLowerCase();var emp=t.indexOf('empresa')>-1;if(a){a.disabled=emp;a.readOnly=emp;if(emp)a.value='';var w=a.closest('#field-apellidos')||a.closest('.field');if(w)w.classList.toggle('opacity-60',emp);}if(rl){rl.disabled=!emp;rl.readOnly=!emp;if(!emp)rl.value='';var w2=rl.closest('#field-representante-legal')||rl.closest('.field');if(w2)w2.classList.toggle('opacity-60',!emp);}})(this)"}),
            'id_tipo_identificacion': forms.Select(attrs={'class': 'w-full select'}),
            'id_estado_cliente': forms.Select(attrs={'class': 'w-full select'}),
        }

    def clean(self):
        cleaned = super().clean()
        # En edición, restaurar valores originales de campos deshabilitados
        # para evitar que manipulaciones del POST los alteren.
        if self.instance and getattr(self.instance, 'pk', None):
            cleaned['id_tipo_cliente'] = self.instance.id_tipo_cliente
            cleaned['id_tipo_identificacion'] = self.instance.id_tipo_identificacion
        tipo = cleaned.get('id_tipo_cliente')
        apellidos = cleaned.get('apellidos')
        representante_legal = cleaned.get('representante_legal')
        nombre_tipo = ''
        if tipo is not None:
            nombre_tipo = (getattr(tipo, 'tipo_cliente', '') or '').strip().lower()

        if 'empresa' in nombre_tipo:
            # Si es Empresa: apellidos se desactiva y representante_legal es obligatorio
            cleaned['apellidos'] = ''
            if not representante_legal:
                self.add_error('representante_legal', 'Representante Legal es obligatorio para Empresa.')
        else:
            # Si es Persona Natural: apellidos es obligatorio y representante_legal se desactiva
            cleaned['representante_legal'] = ''
            if nombre_tipo.startswith('persona') and not apellidos:
                self.add_error('apellidos', 'Apellidos es obligatorio para Persona Natural.')

        return cleaned


@permiso_accion_requerido('clientes.view_cliente', 'ver_clientes')
def listar_clientes(request):
    qs = Cliente.objects.select_related('id_tipo_cliente','id_estado_cliente')
    search = request.GET.get('q','').strip()
    if search:
        qs = qs.filter(
            Q(nombre__icontains=search) |
            Q(apellidos__icontains=search) |
            Q(codigo__icontains=search)
        )
    qs = qs.order_by('nombre','apellidos','id')

    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    try:
        clientes_page = paginator.page(page)
    except PageNotAnInteger:
        clientes_page = paginator.page(1)
    except EmptyPage:
        clientes_page = paginator.page(paginator.num_pages)

    ctx = {
        'clientes': clientes_page,
        'page_obj': clientes_page,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'search': search,
    }
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'clientes/_modal_listar_clientes.html', ctx)
    return render(request, 'clientes/listar_clientes.html', ctx)


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('clientes.add_cliente', 'crear_clientes')
def add_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            try:
                obj.save()
            except IntegrityError:
                # Si existe una restricción única en BD (p.ej. en SQL Server),
                # devolver el error como validación de formulario.
                form.add_error('codigo', 'El código ya existe')
            else:
                obj.refresh_from_db(fields=["codigo"])
                if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                    return listar_clientes(request)
                return redirect('clientes_listar')
            if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
                return render(request, 'clientes/add_clientes.html', {'form': form})
    else:
        form = ClienteForm()
    if request.headers.get('X-Fragment') or request.GET.get('fragment') == '1':
        return render(request, 'clientes/add_clientes.html', {'form': form})
    return render(request, 'clientes/listar_clientes.html', {})


@permiso_accion_requerido('clientes.delete_cliente', 'eliminar_clientes')
def delete_cliente(request, pk):
    c = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        c.delete()
        if request.headers.get('X-Fragment'):
            # tras eliminar devolvemos listado actualizado
            return listar_clientes(request)
        return redirect('clientes_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'clientes/confirm_delete_cliente.html', {'c': c})
    return render(request, 'clientes/listar_clientes.html', {})  # fallback simple


@require_http_methods(["GET","POST"])
@permiso_accion_requerido('clientes.change_cliente', 'editar_clientes')
def edit_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            obj = form.save(commit=False)
            from django.utils import timezone
            obj.updated_at = timezone.now()
            obj.save()
            obj.refresh_from_db(fields=["codigo"])
            if request.headers.get('X-Fragment'):
                return listar_clientes(request)
            return redirect('clientes_listar')
    else:
        form = ClienteForm(instance=cliente)
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'clientes/detail_clientes.html', {'form': form, 'cliente': cliente})
    return render(request, 'clientes/listar_clientes.html', {})
