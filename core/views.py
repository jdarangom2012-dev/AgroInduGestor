from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Group, User
from django.shortcuts import render, redirect
from django import forms
from django.views.decorators.http import require_http_methods
from django.contrib import messages


ROLE_NAMES = ["admin", "operador", "coordinador"]


class LoginForm(forms.Form):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Clases Tailwind + estados focus y transición (safelisteadas para build)
        css = (
            'w-full border border-gray-300 rounded px-3 py-2 text-sm bg-white '
            'focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition'
        )
        self.fields['username'].widget.attrs.update({
            'class': css,
            'autocomplete': 'username'
        })
        self.fields['password'].widget.attrs.update({
            'class': css,
            'autocomplete': 'current-password'
        })


class SignupForm(forms.Form):
    username = forms.CharField(label="Usuario")
    email = forms.EmailField(label="Email")
    first_name = forms.CharField(label="Nombre", required=False)
    last_name = forms.CharField(label="Apellido", required=False)
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repite contraseña", widget=forms.PasswordInput)
    role = forms.ChoiceField(label="Rol", choices=[(r, r.title()) for r in ROLE_NAMES])

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            raise forms.ValidationError("Las contraseñas no coinciden")
        if User.objects.filter(username=data.get("username")).exists():
            raise forms.ValidationError("Usuario ya existe")
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        css = 'w-full border border-gray-300 rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition'
        for name in self.fields:
            self.fields[name].widget.attrs.setdefault('class', css)
        self.fields['password1'].widget.attrs.update({'autocomplete': 'new-password'})
        self.fields['password2'].widget.attrs.update({'autocomplete': 'new-password'})


def _ensure_roles_exist():
    for name in ROLE_NAMES:
        Group.objects.get_or_create(name=name)


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request.POST or None)
    error = None
    if request.method == 'POST' and form.is_valid():
        user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password'])
        if user:
            login(request, user)
            next_url = request.GET.get('next') or request.POST.get('next') or 'dashboard'
            return redirect(next_url)
        error = "Credenciales inválidas"
        messages.error(request, error)
    return render(request, 'auth/login.html', {'form': form, 'error': error, 'next': request.GET.get('next', '')})


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    _ensure_roles_exist()
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data['username'],
            email=form.cleaned_data['email'],
            password=form.cleaned_data['password1'],
            first_name=form.cleaned_data.get('first_name', ''),
            last_name=form.cleaned_data.get('last_name', ''),
        )
        role = form.cleaned_data['role']
        group = Group.objects.get(name=role)
        user.groups.add(group)
        # If role admin give superuser/staff convenience (optional)
        if role == 'admin':
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=['is_staff', 'is_superuser'])
        login(request, user)
        return redirect('dashboard')
    return render(request, 'auth/signup.html', {'form': form})


@login_required
def dashboard_view(request):
    return render(request, 'dashboard/index.html')


@login_required
def manual_usuario_view(request):
    """Manual funcional disponible para cualquier usuario autenticado."""
    return render(request, 'core/manual_usuario.html')
