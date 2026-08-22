from django import forms
from django.core.exceptions import ValidationError
from django.db import connection
from django.forms import BaseFormSet, BaseInlineFormSet, formset_factory, inlineformset_factory


COMPLETADA_PESOS_ERROR = "La tarea no se puede poner en estado completada porque uno o más pesos son menores o iguales a cero."
COMPLETADA_CONFIRMACION_MESSAGE = "No es posible completar la Orden de Producción. Existen procesos de transformación pendientes por confirmar."
COMPLETADA_PROCESOS_PENDIENTES_MESSAGE = "No se puede completar la Orden de Producción porque existen procesos pendientes"
COMPLETADA_PROCESOS_SIN_REGISTRO_MESSAGE = "No se puede completar la Orden de Producción. Existen procesos requeridos sin una orden registrada"
COMPLETADA_CONFIRMATION_RULES = (
    ("trilla", "conf_trilla", "Confir. Trilla"),
    ("selec_cafe_verde", "conf_sel_verde", "Confir. Sel Verde"),
    ("tueste_flag", "conf_tueste", "Confir. Tostado"),
    ("selec_cafe_tostado", "conf_sel_tostado", "Confir. SelecTostado"),
    ("empaque_flag", "conf_empaque", "Confir. Empaque"),
)
COMPLETADA_OPERATIONAL_PROCESS_RULES = (
    ("trilla", "Trilla", "ordenes_trilla", "OrdenTrilla"),
    ("selec_cafe_verde", "Selección Verde", "ordenes_seleccion_verde", "OrdenSeleccionVerde"),
    ("tueste_flag", "Tueste", "tueste", "Tueste"),
    ("selec_cafe_tostado", "Selección Tueste", "seleccion_tueste", "SeleccionTueste"),
    ("empaque_flag", "Empaque", "empaques", "Empaque"),
)

from .models import DetalleEmpaqueOrden, Orden

PARENT_ORDER_COMPLETED_MESSAGE = "No es posible crear o editar esta tarea porque la Orden de Producción vinculada ya se encuentra en estado Completada."


def _normalize_boolean_like(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"true", "1", "on", "yes", "si", "sí"}
    return bool(value)


def get_pending_completion_confirmations(cleaned_data, raw_data=None):
    pending = []
    if cleaned_data is None:
        return pending

    for process_field, confirm_field, label in COMPLETADA_CONFIRMATION_RULES:
        process_enabled = _normalize_boolean_like(cleaned_data.get(process_field))
        confirm_enabled = _normalize_boolean_like(cleaned_data.get(confirm_field))

        if not process_enabled:
            continue
        if confirm_enabled:
            continue

        raw_value = None
        if raw_data is not None:
            raw_value = raw_data.get(process_field)
        if raw_value is not None and not process_enabled:
            process_enabled = _normalize_boolean_like(raw_value)

        raw_confirm_value = None
        if raw_data is not None:
            raw_confirm_value = raw_data.get(confirm_field)
        if raw_confirm_value is not None and not confirm_enabled:
            confirm_enabled = _normalize_boolean_like(raw_confirm_value)

        if process_enabled and not confirm_enabled:
            pending.append(label)

    return pending


def build_completion_validation_message(pending_labels):
    if not pending_labels:
        return COMPLETADA_CONFIRMACION_MESSAGE
    labels = ", ".join(pending_labels)
    return f"{COMPLETADA_CONFIRMACION_MESSAGE} Faltan: {labels}."


def _join_process_labels(labels):
    labels = [str(label) for label in labels if str(label).strip()]
    if len(labels) <= 1:
        return "".join(labels)
    return f"{', '.join(labels[:-1])} y {labels[-1]}"


def build_operational_processes_validation_message(pending_labels, missing_labels):
    messages = []

    if pending_labels:
        messages.append(
            f"{COMPLETADA_PROCESOS_PENDIENTES_MESSAGE}: {_join_process_labels(pending_labels)}."
        )

    if missing_labels:
        messages.append(
            f"{COMPLETADA_PROCESOS_SIN_REGISTRO_MESSAGE}: {_join_process_labels(missing_labels)}."
        )

    return " ".join(messages)


def get_incomplete_operational_processes(cleaned_data, order_id, raw_data=None):
    if cleaned_data is None:
        return [], []

    from django.apps import apps

    pending = []
    missing = []

    for process_field, label, app_label, model_name in COMPLETADA_OPERATIONAL_PROCESS_RULES:
        process_enabled = _normalize_boolean_like(cleaned_data.get(process_field))

        if raw_data is not None and not process_enabled:
            raw_value = raw_data.get(process_field)
            if raw_value is not None:
                process_enabled = _normalize_boolean_like(raw_value)

        if not process_enabled:
            continue

        if not order_id:
            missing.append(label)
            continue

        model = apps.get_model(app_label, model_name)
        qs = model.objects.filter(orden_id=order_id)

        if not qs.exists():
            missing.append(label)
            continue

        if qs.exclude(estado_tareas__estado_tareas__iexact="Completada").exists():
            pending.append(label)

    return pending, missing


def _normalize_order_state_name(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().lower()
    return (getattr(value, "estado_orden", "") or "").strip().lower()


def is_parent_order_completed(orden):
    if orden is None:
        return False
    return _normalize_order_state_name(getattr(orden, "estado_orden", None)) == "completada"


def enforce_parent_order_not_completed(form, field_name="orden"):
    order = None
    if getattr(form, "is_bound", False):
        order = form.cleaned_data.get(field_name)
    if order is None:
        order = getattr(getattr(form, "instance", None), field_name, None)
    if order is not None and is_parent_order_completed(order):
        form.add_error(field_name, PARENT_ORDER_COMPLETED_MESSAGE)
        return False
    return True


class ParentOrderChoiceField(forms.ModelChoiceField):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value in (None, ""):
            return option
        try:
            instance = self.queryset.get(pk=value)
        except Exception:
            instance = None
        if instance is not None:
            option["attrs"]["data-parent-order-completed"] = "1" if is_parent_order_completed(instance) else "0"
        return option


def _append_widget_classes(field, extra_classes):
    existing = field.widget.attrs.get("class", "").strip()
    extras = [value for value in extra_classes.split() if value]
    class_names = existing.split() if existing else []

    for class_name in extras:
        if class_name not in class_names:
            class_names.append(class_name)

    field.widget.attrs["class"] = " ".join(class_names)


class OrdenForm(forms.ModelForm):
    BOOLEAN_CHOICES = (
        (True, "Sí"),
        (False, "No"),
    )

    id_empleado = forms.ModelChoiceField(queryset=None, required=False, widget=forms.Select(attrs={"class": "w-full select"}))
    conf_sel_tostado = forms.TypedChoiceField(
        choices=BOOLEAN_CHOICES,
        coerce=lambda value: value if isinstance(value, bool) else str(value).lower() == "true",
        empty_value=False,
        required=False,
        initial=False,
        widget=forms.Select(attrs={"class": "w-full select"}),
    )

    def cafe_label_from_instance(self, obj):
        codigo = (getattr(obj, "codigo", None) or "").strip()
        descripcion = (getattr(obj, "descripcion", None) or "").strip()

        if codigo and descripcion:
            return f"{codigo} - {descripcion}"
        if codigo:
            return codigo
        if descripcion:
            return descripcion
        return str(obj)

    id_inven_cafe = forms.ModelChoiceField(queryset=None, required=False, label="Café", widget=forms.Select(attrs={"class": "w-full select"}))
    variedad_cafe = forms.ModelChoiceField(queryset=None, required=False, label="Variedad Café", widget=forms.Select(attrs={"class": "w-full select"}))
    proceso_inventario_cafe = forms.ModelChoiceField(queryset=None, required=False, label="Proceso Inventario Café", widget=forms.Select(attrs={"class": "w-full select"}))
    empaque_cafe = forms.ModelChoiceField(queryset=None, required=False, label="Empaque Café", widget=forms.Select(attrs={"class": "w-full select"}))
    tamano_empaque = forms.ModelChoiceField(queryset=None, required=False, label="Tamaño Empaque", widget=forms.Select(attrs={"class": "w-full select"}))
    sacos_entero = forms.IntegerField(required=False, min_value=0)
    peso_bruto = forms.FloatField(required=False, min_value=0)
    peso = forms.FloatField(required=False, min_value=0)
    trabajo_empaque = forms.BooleanField(required=False)
    etiqueta_invima = forms.BooleanField(required=False)

    # Usar solo fecha (sin hora) en el formulario
    # Acepta DD/MM/YYYY y también ISO (fallback de los inputs type=date)
    fecha_inicio_orden = forms.DateField(required=False, input_formats=["%d/%m/%Y", "%Y-%m-%d"])
    fecha_entrega = forms.DateField(required=False, input_formats=["%d/%m/%Y", "%Y-%m-%d"])

    class Meta:
        model = Orden
        fields = [
            "orden",
            "cliente",
            "estado_orden",
            "id_empleado",
            "id_inven_cafe",
            "variedad_cafe",
            "proceso_inventario_cafe",
            "empaque_cafe",
            "tamano_empaque",
            "fecha_inicio_orden",
            "fecha_entrega",
            "notas",
            "sacos_entero",
            "peso_bruto",
            "peso",
            "trabajo_empaque",
            "etiqueta_invima",
            "trilla",
            "selec_cafe_verde",
            "tueste_flag",
            "selec_cafe_tostado",
            "empaque_flag",
            "conf_trilla",
            "conf_sel_verde",
            "conf_tueste",
            "conf_sel_tostado",
            "conf_empaque",
            "prioridad",
        ]
        widgets = {
            "id_empleado": forms.Select(attrs={"class": "w-full select"}),
            "id_inven_cafe": forms.Select(attrs={"class": "w-full select"}),
            "variedad_cafe": forms.Select(attrs={"class": "w-full select"}),
            "proceso_inventario_cafe": forms.Select(attrs={"class": "w-full select"}),
            "empaque_cafe": forms.Select(attrs={"class": "w-full select"}),
            "tamano_empaque": forms.Select(attrs={"class": "w-full select"}),
            "sacos_entero": forms.NumberInput(attrs={"class": "w-full input", "placeholder": "Sacos enteros"}),
            "peso_bruto": forms.NumberInput(
                attrs={"class": "w-full input", "placeholder": "Peso bruto (kg)", "step": "0.01"}
            ),
            "peso": forms.NumberInput(attrs={"class": "w-full input", "placeholder": "Peso neto (kg)", "step": "0.01"}),
            "trabajo_empaque": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "etiqueta_invima": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "orden": forms.TextInput(attrs={"class": "w-full input", "placeholder": "Código de orden"}),
            "cliente": forms.Select(attrs={"class": "w-full select"}),
            "estado_orden": forms.Select(attrs={"class": "w-full select"}),
            "fecha_inicio_orden": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "input-form w-full input",
                    "data-datepicker": "1",
                    "data-dp-no-opener": "1",
                }
            ),
            "fecha_entrega": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "input-form w-full input",
                    "data-datepicker": "1",
                    "data-dp-no-opener": "1",
                }
            ),
            "notas": forms.TextInput(attrs={"class": "w-full input"}),
            "prioridad": forms.NumberInput(attrs={"class": "w-full input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from clientes.models import Cliente
        from empleados.models import Empleado
        from estado_ordenes.models import EstadoOrden
        from inventario_cafe.models import InventarioCafe
        from variedad_cafe.models import VariedadCafe
        from proceso_inven_cafe.models import ProcesoInvenCafe
        from cafe_empaque.models import CafeEmpaque
        from tamano_empaque.models import TamanoEmpaque

        self.fields["cliente"].queryset = Cliente.objects.all().order_by('apellidos', 'nombre', 'id')
        self.fields["estado_orden"].queryset = EstadoOrden.objects.all().order_by('estado_orden', 'id')
        estado_pendiente = EstadoOrden.objects.filter(estado_orden__iexact="Pendiente").order_by('id').first()
        self.fields["id_empleado"].queryset = Empleado.objects.all()
        self.fields["id_inven_cafe"].queryset = InventarioCafe.objects.all()
        self.fields["variedad_cafe"].queryset = VariedadCafe.objects.all().order_by('variedad_cafe', 'id')
        self.fields["proceso_inventario_cafe"].queryset = ProcesoInvenCafe.objects.all().order_by('proceso_inven_cafe', 'id')
        self.fields["empaque_cafe"].queryset = CafeEmpaque.objects.all().order_by('empaque_cafe', 'id')
        self.fields["tamano_empaque"].queryset = TamanoEmpaque.objects.all().order_by('tamano_empaque', 'id')
        self.fields["id_inven_cafe"].label_from_instance = self.cafe_label_from_instance

        if hasattr(self.fields.get("cliente", None), "empty_label"):
            self.fields["cliente"].empty_label = "Seleccione…"
        if hasattr(self.fields.get("estado_orden", None), "empty_label"):
            self.fields["estado_orden"].empty_label = "Seleccione…"
        if hasattr(self.fields.get("id_empleado", None), "empty_label"):
            self.fields["id_empleado"].empty_label = "Seleccione…"
        if hasattr(self.fields.get("id_inven_cafe", None), "empty_label"):
            self.fields["id_inven_cafe"].empty_label = "Seleccione…"
        if hasattr(self.fields.get("variedad_cafe", None), "empty_label"):
            self.fields["variedad_cafe"].empty_label = "Seleccione…"
        if hasattr(self.fields.get("proceso_inventario_cafe", None), "empty_label"):
            self.fields["proceso_inventario_cafe"].empty_label = "Seleccione…"
        if hasattr(self.fields.get("empaque_cafe", None), "empty_label"):
            self.fields["empaque_cafe"].empty_label = "Seleccione…"
        if hasattr(self.fields.get("tamano_empaque", None), "empty_label"):
            self.fields["tamano_empaque"].empty_label = "Seleccione…"

        if estado_pendiente is not None and not getattr(self.instance, "pk", None) and not self.is_bound:
            self.fields["estado_orden"].initial = estado_pendiente.pk
            self.initial["estado_orden"] = estado_pendiente.pk

        confirmacion_fields = (
            "conf_trilla",
            "conf_sel_verde",
            "conf_tueste",
            "conf_sel_tostado",
            "conf_empaque",
        )
        if not self.is_bound:
            for field_name in confirmacion_fields:
                if field_name not in self.fields:
                    continue
                current_value = getattr(self.instance, field_name, None)
                normalized_value = False if current_value is None else current_value
                self.fields[field_name].initial = normalized_value
                self.initial[field_name] = normalized_value

        if "conf_sel_tostado" in self.fields:
            current_value = getattr(self.instance, "conf_sel_tostado", None)
            normalized_value = False if current_value is None else bool(current_value)
            if not self.is_bound:
                self.fields["conf_sel_tostado"].initial = normalized_value
                self.initial["conf_sel_tostado"] = normalized_value

        for _name, field in self.fields.items():
            field.disabled = False
            try:
                field.widget.attrs.pop("disabled", None)
                field.widget.attrs.pop("readonly", None)
            except Exception:
                pass

        date_attrs = {
            "type": "date",
            "class": "input-form w-full input",
            "data-datepicker": "1",
            "data-dp-no-opener": "1",
        }
        if "fecha_inicio_orden" in self.fields:
            try:
                self.fields["fecha_inicio_orden"].widget = forms.DateInput(attrs=date_attrs)
            except Exception:
                pass
        if "fecha_entrega" in self.fields:
            try:
                self.fields["fecha_entrega"].widget = forms.DateInput(attrs=date_attrs)
            except Exception:
                pass

        numeric_fields = (
            "sacos_entero",
            "peso_bruto",
            "peso",
            "prioridad",
        )
        numeric_field_classes = "border rounded-xl bg-white px-3 py-2 text-right"

        for field_name in numeric_fields:
            if field_name in self.fields:
                _append_widget_classes(self.fields[field_name], numeric_field_classes)

    def clean_orden(self):
        raw = self.cleaned_data.get("orden") or ""
        orden = raw.strip().upper()

        if not orden:
            return None

        qs = Orden.objects.filter(orden__iexact=orden)
        if getattr(self.instance, "pk", None):
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("La orden de producción ya existe")

        return orden

    def clean_fecha_entrega(self):
        from datetime import datetime
        from django.utils import timezone

        d = self.cleaned_data.get("fecha_entrega")
        if d:
            dt = datetime.combine(d, datetime.min.time())
            return timezone.make_aware(dt)
        return d

    def clean_fecha_inicio_orden(self):
        from datetime import datetime
        from django.utils import timezone

        d = self.cleaned_data.get("fecha_inicio_orden")
        if d:
            dt = datetime.combine(d, datetime.min.time())
            return timezone.make_aware(dt)
        return d

    def clean(self):
        cleaned = super().clean()

        def field_enabled(field_name):
            value = cleaned.get(field_name)
            if value is not None:
                return bool(value)

            raw_value = self.data.get(field_name)
            normalized = str(raw_value or "").strip().lower()
            return normalized in {"true", "1", "on", "yes", "si", "sí"}

        orden = cleaned.get("orden")
        if (orden is None or str(orden).strip() == "") and "orden" not in self.errors:
            self.add_error("orden", "No se puede guardar: la orden es obligatoria")

        fecha_inicio = cleaned.get("fecha_inicio_orden")
        if (not fecha_inicio) and "fecha_inicio_orden" not in self.errors:
            self.add_error("fecha_inicio_orden", "No se puede guardar: la fecha de inicio es obligatoria")

        peso_bruto = cleaned.get("peso_bruto")
        peso = cleaned.get("peso")
        if peso_bruto is not None and peso is not None and peso > peso_bruto:
            self.add_error("peso", "El peso neto debe ser menor o igual al peso bruto.")

        estado_orden = cleaned.get("estado_orden")
        estado_nombre = (getattr(estado_orden, "estado_orden", "") or "").strip().lower()
        if estado_nombre == "completada":
            pesos_requeridos = (peso_bruto, peso)
            if any(valor is None or valor <= 0 for valor in pesos_requeridos):
                raise ValidationError(COMPLETADA_PESOS_ERROR)

            pending_confirmations = get_pending_completion_confirmations(cleaned, self.data)
            if pending_confirmations:
                self.add_error(None, build_completion_validation_message(pending_confirmations))

            pending_processes, missing_processes = get_incomplete_operational_processes(
                cleaned,
                getattr(self.instance, "pk", None),
                self.data,
            )
            if pending_processes or missing_processes:
                self.add_error(
                    None,
                    build_operational_processes_validation_message(pending_processes, missing_processes),
                )

        trabajo_empaque = bool(cleaned.get("trabajo_empaque"))
        empaque_flag = field_enabled("empaque_flag")
        conf_empaque = field_enabled("conf_empaque")
        empaque_cafe = cleaned.get("empaque_cafe")
        tamano_empaque = cleaned.get("tamano_empaque")
        detalle_total_forms = 0
        detalle_con_valores = False

        if self.is_bound:
            try:
                detalle_total_forms = int(self.data.get("detalle_empaque-TOTAL_FORMS") or 0)
            except (TypeError, ValueError):
                detalle_total_forms = 0

            for index in range(detalle_total_forms):
                prefix = f"detalle_empaque-{index}"
                if any(
                    str(self.data.get(f"{prefix}-{field_name}") or "").strip()
                    for field_name in ("empaque_cafe", "tamano_empaque", "cantidad")
                ):
                    detalle_con_valores = True
                    break

        usa_empaque = (
            trabajo_empaque
            or detalle_con_valores
            or empaque_flag
            or conf_empaque
            or empaque_cafe is not None
            or tamano_empaque is not None
        )

        if not usa_empaque:
            cleaned["empaque_cafe"] = None
            cleaned["tamano_empaque"] = None

        return cleaned


class DetalleEmpaqueOrdenForm(forms.ModelForm):
    class Meta:
        model = DetalleEmpaqueOrden
        fields = ["empaque_cafe", "tamano_empaque", "cantidad"]
        widgets = {
            "empaque_cafe": forms.Select(attrs={"class": "w-full select"}),
            "tamano_empaque": forms.Select(attrs={"class": "w-full select"}),
            "cantidad": forms.NumberInput(attrs={"class": "w-full input", "min": "1", "step": "1", "placeholder": "Cantidad"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from cafe_empaque.models import CafeEmpaque
        from tamano_empaque.models import TamanoEmpaque

        self.fields["empaque_cafe"].queryset = CafeEmpaque.objects.all().order_by('empaque_cafe', 'id')
        self.fields["tamano_empaque"].queryset = TamanoEmpaque.objects.all().order_by('tamano_empaque', 'id')
        self.fields["empaque_cafe"].required = False
        self.fields["tamano_empaque"].required = False
        self.fields["cantidad"].required = False
        self.fields["cantidad"].min_value = 1
        self.fields["empaque_cafe"].empty_label = "Seleccione…"
        self.fields["tamano_empaque"].empty_label = "Seleccione…"
        _append_widget_classes(self.fields["cantidad"], "border rounded-xl bg-white px-3 py-2 text-right")

    def clean(self):
        cleaned = super().clean()
        empaque_cafe = cleaned.get("empaque_cafe")
        tamano_empaque = cleaned.get("tamano_empaque")
        cantidad = cleaned.get("cantidad")
        has_any = empaque_cafe is not None or tamano_empaque is not None or cantidad is not None

        if not has_any:
            return cleaned

        if empaque_cafe is None:
            self.add_error("empaque_cafe", "Seleccione un Empaque Café.")

        if tamano_empaque is None:
            self.add_error("tamano_empaque", "Seleccione un Tamaño Empaque.")

        if cantidad in (None, ""):
            self.add_error("cantidad", "Ingrese una cantidad.")

        return cleaned


class BaseDetalleEmpaqueOrdenFormSet(BaseInlineFormSet):
    def _field_enabled(self, field_name):
        raw_value = self.data.get(field_name)
        normalized = str(raw_value or "").strip().lower()
        return normalized in {"true", "1", "on", "yes", "si", "sí"}

    def requiere_detalle(self):
        return self._field_enabled("trabajo_empaque")

    def clean(self):
        super().clean()

        filas_completas = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            cleaned = form.cleaned_data
            empaque_cafe = cleaned.get("empaque_cafe")
            tamano_empaque = cleaned.get("tamano_empaque")
            cantidad = cleaned.get("cantidad")
            has_any = empaque_cafe is not None or tamano_empaque is not None or cantidad is not None

            if not has_any:
                continue

            if empaque_cafe is not None and tamano_empaque is not None and cantidad is not None:
                filas_completas += 1

        if self.requiere_detalle() and filas_completas == 0:
            raise ValidationError("Debe registrar al menos un detalle de empaque cuando Trajo Empaque está activo.")


class BaseDetalleEmpaqueFallbackFormSet(BaseFormSet):
    uses_legacy_storage = True

    def _field_enabled(self, field_name):
        raw_value = self.data.get(field_name)
        normalized = str(raw_value or "").strip().lower()
        return normalized in {"true", "1", "on", "yes", "si", "sí"}

    def requiere_detalle(self):
        return self.is_bound and self._field_enabled("trabajo_empaque")

    def clean(self):
        super().clean()

        filas_completas = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            cleaned = form.cleaned_data
            empaque_cafe = cleaned.get("empaque_cafe")
            tamano_empaque = cleaned.get("tamano_empaque")
            cantidad = cleaned.get("cantidad")
            has_any = empaque_cafe is not None or tamano_empaque is not None or cantidad is not None

            if not has_any:
                continue

            if empaque_cafe is not None and tamano_empaque is not None and cantidad is not None:
                filas_completas += 1

        if self.requiere_detalle() and filas_completas == 0:
            raise ValidationError("Debe registrar al menos un detalle de empaque cuando Trajo Empaque está activo.")


DetalleEmpaqueOrdenFormSet = inlineformset_factory(
    Orden,
    DetalleEmpaqueOrden,
    form=DetalleEmpaqueOrdenForm,
    formset=BaseDetalleEmpaqueOrdenFormSet,
    extra=1,
    can_delete=False,
)


DetalleEmpaqueOrdenFallbackFormSet = formset_factory(
    DetalleEmpaqueOrdenForm,
    formset=BaseDetalleEmpaqueFallbackFormSet,
    extra=1,
)


def detalle_empaque_table_exists():
    try:
        return DetalleEmpaqueOrden._meta.db_table in connection.introspection.table_names()
    except Exception:
        return False


def build_detalle_empaque_formset(*, data=None, instance=None):
    if not detalle_empaque_table_exists():
        initial = []
        if instance is not None and (instance.empaque_cafe_id or instance.tamano_empaque_id):
            initial.append(
                {
                    "empaque_cafe": instance.empaque_cafe_id,
                    "tamano_empaque": instance.tamano_empaque_id,
                    "cantidad": None,
                }
            )

        if data is not None and "detalle_empaque-TOTAL_FORMS" not in data:
            data = None

        fallback_formset = DetalleEmpaqueOrdenFallbackFormSet(
            data=data,
            initial=initial,
            prefix="detalle_empaque",
        )
        fallback_formset.instance = instance
        return fallback_formset

    if data is not None and "detalle_empaque-TOTAL_FORMS" not in data:
        data = None
    return DetalleEmpaqueOrdenFormSet(data=data, instance=instance, prefix="detalle_empaque")
