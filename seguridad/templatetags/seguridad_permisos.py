from __future__ import annotations

from django import template

from seguridad.helpers import (
    es_programador,
    tiene_modulo as _tiene_modulo,
    puede_editar_campo,
    puede_ver_campo,
    tiene_permiso_accion as _tiene_permiso_accion,
    tiene_permiso_grupo as _tiene_permiso_grupo,
    tiene_permiso as _tiene_permiso,
)

register = template.Library()


@register.simple_tag
def tiene_permiso(user, codigo: str) -> bool:
    return _tiene_permiso(user, codigo)


@register.simple_tag
def tiene_modulo(user, nombre_modulo: str) -> bool:
    return _tiene_modulo(user, nombre_modulo)


@register.simple_tag
def tiene_permiso_accion(user, django_perm: str | None = None, codigo: str | None = None) -> bool:
    return _tiene_permiso_accion(user, django_perm=django_perm, codigo=codigo)


@register.simple_tag
def tiene_permiso_grupo(user, django_perm: str) -> bool:
    return _tiene_permiso_grupo(user, django_perm)


@register.simple_tag
def es_programador_tag(user) -> bool:
    return es_programador(user)


@register.simple_tag
def puede_editar_campo_tag(user, modelo: str, campo: str) -> bool:
    return puede_editar_campo(user, modelo, campo)


@register.simple_tag
def puede_ver_campo_tag(user, modelo: str, campo: str) -> bool:
    return puede_ver_campo(user, modelo, campo)


@register.simple_tag
def render_field_con_permiso(bound_field, user, modelo: str, campo: str):
    """Renderiza un BoundField como editable o readonly según permisos.

    Uso:
      {% render_field_con_permiso form.mi_campo request.user "app.Model" "mi_campo" %}

    Nota: Este tag no modifica estilos globales y solo afecta al campo renderizado.
    """
    if not puede_ver_campo(user, modelo, campo):
        return ''

    editable = puede_editar_campo(user, modelo, campo)
    widget = bound_field.field.widget
    input_type = getattr(widget, 'input_type', '')

    attrs = {}
    if not editable:
        # readonly no aplica a select/checkbox; usamos disabled como fallback.
        if input_type in {'select', 'selectmultiple', 'checkbox', 'radio', 'file'}:
            attrs['disabled'] = 'disabled'
        else:
            attrs['readonly'] = 'readonly'
        attrs['aria-readonly'] = 'true'

    return bound_field.as_widget(attrs=attrs)
