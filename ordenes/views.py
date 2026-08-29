import logging
from html import escape

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.db import IntegrityError, DatabaseError, transaction
from django.utils import timezone
from seguridad.decorators import permiso_accion_requerido
from .models import Orden
from .forms import (
    OrdenForm,
    build_completion_validation_message,
    build_detalle_empaque_formset,
    detalle_empaque_table_exists,
    get_pending_completion_confirmations,
)


logger = logging.getLogger(__name__)


def _catalogos_nueva_orden_snapshot():
    from clientes.models import Cliente
    from empleados.models import Empleado
    from estado_ordenes.models import EstadoOrden
    from inventario_cafe.models import InventarioCafe
    from cafe_empaque.models import CafeEmpaque
    from tamano_empaque.models import TamanoEmpaque

    snapshot = {
        'clientes_count': Cliente.objects.count(),
        'empleados_count': Empleado.objects.count(),
        'estados_orden_count': EstadoOrden.objects.count(),
        'inventario_cafe_count': InventarioCafe.objects.count(),
        'cafe_empaque_count': CafeEmpaque.objects.count(),
        'tamano_empaque_count': TamanoEmpaque.objects.count(),
    }
    return snapshot


def _obtener_estado_orden_pendiente():
    from estado_ordenes.models import EstadoOrden

    return EstadoOrden.objects.filter(estado_orden__iexact='Pendiente').order_by('id').first()


def _error_real_response(message: str, error: Exception, status_code: int = 500):
    detail = escape(str(error))
    return HttpResponse(
        f'{message}: {detail}',
        status=status_code,
        content_type='text/plain; charset=utf-8',
    )


def _validar_estado_completada_en_vista(form):
    if not form.is_valid():
        return False

    estado_orden = form.cleaned_data.get('estado_orden')
    estado_nombre = (getattr(estado_orden, 'estado_orden', '') or '').strip().lower()
    if estado_nombre != 'completada':
        return True

    pending_confirmations = get_pending_completion_confirmations(form.cleaned_data, form.data)
    if pending_confirmations:
        form.add_error(None, build_completion_validation_message(pending_confirmations))
        return False

    return True


def _render_add_orden_form(request, form, detalle_formset):
    missing_fields = [
        field_name
        for field_name in ('cliente', 'id_empleado', 'estado_orden', 'id_inven_cafe', 'variedad_cafe', 'proceso_inventario_cafe', 'empaque_cafe', 'tamano_empaque')
        if field_name not in form.fields
    ]
    has_estado_inven_cafe = 'estado_inven_cafe' in form.fields

    logger.info(
        'Antes de render add_orden template=ordenes/add_OrdenesProduccion.html missing_fields=%s has_estado_inven_cafe=%s',
        missing_fields,
        has_estado_inven_cafe,
    )
    print(
        f"[ORDENES DEBUG] before_render_add_orden template=ordenes/add_OrdenesProduccion.html "
        f"missing_fields={missing_fields} has_estado_inven_cafe={has_estado_inven_cafe}"
    )

    return render(request, 'ordenes/add_OrdenesProduccion.html', {'form': form, 'detalle_formset': detalle_formset})


def _append_css_class(widget, extra_class):
    current = widget.attrs.get('class', '').strip()
    classes = current.split() if current else []
    if extra_class not in classes:
        classes.append(extra_class)
    widget.attrs['class'] = ' '.join(classes)


def _build_view_orden_context(obj):
    form = OrdenForm(instance=obj)

    for field in form.fields.values():
        field.disabled = True
        field.widget.attrs['disabled'] = 'disabled'
        field.widget.attrs['aria-readonly'] = 'true'
        _append_css_class(field.widget, 'bg-gray-100')
        _append_css_class(field.widget, 'text-gray-500')
        _append_css_class(field.widget, 'cursor-not-allowed')
        _append_css_class(field.widget, 'opacity-90')

    detalle_empaque_rows = []
    if detalle_empaque_table_exists():
        detalle_empaque_rows = list(
            obj.detalles_empaque.select_related('empaque_cafe', 'tamano_empaque').order_by('id')
        )
    elif obj.empaque_cafe_id or obj.tamano_empaque_id:
        detalle_empaque_rows = [
            {
                'empaque_cafe': obj.empaque_cafe,
                'tamano_empaque': obj.tamano_empaque,
                'cantidad': None,
            }
        ]

    return {
        'form': form,
        'obj': obj,
        'detalle_empaque_rows': detalle_empaque_rows,
    }


def _save_detalle_empaque(instance, form, detalle_formset):
    trabajo_empaque = bool(form.cleaned_data.get('trabajo_empaque'))

    if getattr(detalle_formset, 'uses_legacy_storage', False):
        empaque_cafe = None
        tamano_empaque = None

        if trabajo_empaque:
            for detalle_form in detalle_formset.forms:
                if not hasattr(detalle_form, 'cleaned_data'):
                    continue

                cleaned = detalle_form.cleaned_data
                if not cleaned:
                    continue

                if cleaned.get('empaque_cafe') and cleaned.get('tamano_empaque'):
                    empaque_cafe = cleaned.get('empaque_cafe')
                    tamano_empaque = cleaned.get('tamano_empaque')
                    break

        instance.empaque_cafe = empaque_cafe
        instance.tamano_empaque = tamano_empaque
        instance.save(update_fields=['empaque_cafe', 'tamano_empaque'])
        return

    if not trabajo_empaque:
        instance.detalles_empaque.all().delete()
        changed = instance.empaque_cafe_id is not None or instance.tamano_empaque_id is not None
        if changed:
            instance.empaque_cafe = None
            instance.tamano_empaque = None
            instance.save(update_fields=['empaque_cafe', 'tamano_empaque'])
        return

    detalle_formset.instance = instance
    detalle_formset.save()

    primer_detalle = instance.detalles_empaque.order_by('id').first()
    empaque_cafe_id = primer_detalle.empaque_cafe_id if primer_detalle else None
    tamano_empaque_id = primer_detalle.tamano_empaque_id if primer_detalle else None

    if instance.empaque_cafe_id != empaque_cafe_id or instance.tamano_empaque_id != tamano_empaque_id:
        instance.empaque_cafe_id = empaque_cafe_id
        instance.tamano_empaque_id = tamano_empaque_id
        instance.save(update_fields=['empaque_cafe', 'tamano_empaque'])


@permiso_accion_requerido('ordenes.view_orden', 'ver_orden_produccion')
def listar_ordenes(request):
    qs = Orden.objects.select_related('cliente', 'estado_orden', 'empaque_cafe', 'tamano_empaque').order_by('-fecha_inicio_orden', '-id')
    search = request.GET.get('q', '').strip()
    if search:
        q = (
            Q(orden__icontains=search) |
            Q(cliente__nombre__icontains=search) |
            Q(cliente__apellidos__icontains=search) |
            Q(estado_orden__estado_orden__icontains=search) |
            Q(id_inven_cafe__codigo__icontains=search) |
            Q(id_inven_cafe__descripcion__icontains=search) |
            Q(notas__icontains=search)
        )
        qs = qs.filter(q)
    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    try:
        ordenes = paginator.page(page)
    except PageNotAnInteger:
        ordenes = paginator.page(1)
    except EmptyPage:
        ordenes = paginator.page(paginator.num_pages)
    ctx = {
        'ordenes': ordenes,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'search': search
    }
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'ordenes/_modal_listar_OrdenesProduccion.html', ctx)
    return render(request, 'ordenes/listar_OrdenesProduccion.html', ctx)


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('ordenes.add_orden', 'crear_orden_produccion')
def add_orden(request):
    is_htmx = request.headers.get('HX-Request') == 'true'
    logger.info('Entrando a add_orden method=%s htmx=%s path=%s', request.method, is_htmx, request.path)
    print(f"[ORDENES DEBUG] add_orden method={request.method} htmx={is_htmx} path={request.path}")

    try:
        catalogos = _catalogos_nueva_orden_snapshot()
    except Exception as error:
        logger.exception('Error validando catálogos para nueva orden')
        print(f"[ORDENES DEBUG] catalog_error={error}")
        return _error_real_response('Error real validando catálogos de Nueva Orden de Producción', error)

    logger.info('Catálogos nueva orden: %s', catalogos)
    print(f"[ORDENES DEBUG] catalogos_nueva_orden={catalogos}")

    if request.method == 'POST':
        try:
            form = OrdenForm(request.POST)
            detalle_formset = build_detalle_empaque_formset(data=request.POST)
        except Exception as error:
            logger.exception('Error construyendo OrdenForm en POST add_orden')
            print(f"[ORDENES DEBUG] post_form_build_error={error}")
            return _error_real_response('Error real construyendo el formulario de Nueva Orden de Producción', error)

        detalle_formset_valid = (not detalle_formset.is_bound) or detalle_formset.is_valid()
        if form.is_valid() and detalle_formset_valid:
            if not _validar_estado_completada_en_vista(form):
                return _render_add_orden_form(request, form, detalle_formset)
            obj = form.save(commit=False)
            if obj.estado_orden_id is None:
                obj.estado_orden = _obtener_estado_orden_pendiente()
            if not obj.fecha_ingreso:
                obj.fecha_ingreso = timezone.now()
            if not obj.created_at:
                obj.created_at = timezone.now()
            defaults = {
                'cliente': obj.cliente,
                'estado_orden': obj.estado_orden,
                'id_empleado': obj.id_empleado,
                'id_inven_cafe': obj.id_inven_cafe,
                'variedad_cafe': obj.variedad_cafe,
                'proceso_inventario_cafe': obj.proceso_inventario_cafe,
                'empaque_cafe': obj.empaque_cafe,
                'tamano_empaque': obj.tamano_empaque,
                'fecha_inicio_orden': obj.fecha_inicio_orden,
                'fecha_entrega': obj.fecha_entrega,
                'notas': obj.notas,
                'sacos_entero': obj.sacos_entero,
                'peso_bruto': obj.peso_bruto,
                'peso': obj.peso,
                'trabajo_empaque': obj.trabajo_empaque,
                'etiqueta_invima': obj.etiqueta_invima,
                'trilla': obj.trilla,
                'selec_cafe_verde': obj.selec_cafe_verde,
                'tueste_flag': obj.tueste_flag,
                'selec_cafe_tostado': obj.selec_cafe_tostado,
                'molienda_flag': obj.molienda_flag,
                'empaque_flag': obj.empaque_flag,
                'conf_trilla': obj.conf_trilla,
                'conf_sel_verde': obj.conf_sel_verde,
                'conf_tueste': obj.conf_tueste,
                'conf_sel_tostado': obj.conf_sel_tostado,
                'conf_molienda': obj.conf_molienda,
                'conf_empaque': obj.conf_empaque,
                'prioridad': obj.prioridad,
                'fecha_ingreso': obj.fecha_ingreso,
                'created_at': obj.created_at,
            }
            try:
                with transaction.atomic():
                    if obj.orden:
                        instance, created = Orden.objects.get_or_create(orden=obj.orden, defaults=defaults)
                        if not created:
                            form.add_error('orden', 'La orden de producción ya existe')
                    else:
                        # fallback key: cliente + fecha_ingreso
                        instance, created = Orden.objects.get_or_create(cliente=obj.cliente, fecha_ingreso=obj.fecha_ingreso, defaults={**defaults, 'orden': obj.orden})
                    if not created:
                        # Mantener comportamiento existente solo para el fallback sin código.
                        if not obj.orden:
                            for k, v in defaults.items():
                                setattr(instance, k, v)
                            instance.updated_at = timezone.now()
                            instance.save()
                    if not form.errors:
                        _save_detalle_empaque(instance, form, detalle_formset)
            except (IntegrityError, DatabaseError) as e:
                logger.exception('Error capturado al guardar nueva orden')
                print(f"[ORDENES DEBUG] save_error={e}")
                form.add_error(None, f'Error al guardar en base de datos: {e}')
            else:
                if not form.errors:
                    messages.success(request, 'Orden creada correctamente.')
                    if is_htmx:
                        response = HttpResponse(status=204)
                        response['HX-Redirect'] = reverse('ordenes_produccion_listar')
                        return response
                    return redirect('ordenes_produccion_listar')
    else:
        try:
            form = OrdenForm()
            detalle_formset = build_detalle_empaque_formset()
        except Exception as error:
            logger.exception('Error construyendo OrdenForm en GET add_orden')
            print(f"[ORDENES DEBUG] get_form_build_error={error}")
            return _error_real_response('Error real construyendo el formulario de Nueva Orden de Producción', error)

    try:
        return _render_add_orden_form(request, form, detalle_formset)
    except Exception as error:
        logger.exception('Error renderizando el formulario de Nueva Orden de Producción')
        print(f"[ORDENES DEBUG] render_error={error}")
        return _error_real_response('Error real renderizando el formulario de Nueva Orden de Producción', error)


@require_http_methods(["GET", "POST"])
@permiso_accion_requerido('ordenes.change_orden', 'editar_orden_produccion')
def edit_orden(request, pk):
    obj = get_object_or_404(Orden, pk=pk)
    is_modal_request = (
        request.GET.get('fragment') == '1'
        or request.headers.get('X-Fragment')
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )
    if request.method == 'POST':
        form = OrdenForm(request.POST, instance=obj)
        detalle_formset = build_detalle_empaque_formset(data=request.POST, instance=obj)
        detalle_formset_valid = (not detalle_formset.is_bound) or detalle_formset.is_valid()
        if form.is_valid() and detalle_formset_valid:
            if not _validar_estado_completada_en_vista(form):
                return render(request, 'ordenes/detail_OrdenesProduccion.html', {'form': form, 'obj': obj, 'detalle_formset': detalle_formset})
            inst = form.save(commit=False)
            inst.updated_at = timezone.now()
            try:
                with transaction.atomic():
                    inst.save()
                    _save_detalle_empaque(inst, form, detalle_formset)
            except (IntegrityError, DatabaseError) as e:
                form.add_error(None, f'Error al guardar en base de datos: {e}')
            else:
                messages.success(request, 'Orden actualizada correctamente.')
                if is_modal_request:
                    return listar_ordenes(request)
                return redirect('ordenes_produccion_listar')
    else:
        form = OrdenForm(instance=obj)
        detalle_formset = build_detalle_empaque_formset(instance=obj)
    return render(request, 'ordenes/detail_OrdenesProduccion.html', {'form': form, 'obj': obj, 'detalle_formset': detalle_formset})


@require_http_methods(["GET"])
@permiso_accion_requerido('ordenes.view_orden', 'ver_orden_produccion')
def view_orden(request, pk):
    obj = get_object_or_404(Orden, pk=pk)
    return render(request, 'ordenes/view_OrdenesProduccion.html', _build_view_orden_context(obj))


@permiso_accion_requerido('ordenes.delete_orden', 'eliminar_orden_produccion')
def delete_orden(request, pk):
    obj = get_object_or_404(Orden, pk=pk)
    if request.method == 'POST':
        obj.delete()
        if request.headers.get('X-Fragment'):
            return listar_ordenes(request)
        return redirect('ordenes_produccion_listar')
    if request.GET.get('fragment') == '1' or request.headers.get('X-Fragment'):
        return render(request, 'ordenes/confirm_delete_OrdenesProduccion.html', {'obj': obj})
    return render(request, 'ordenes/listar_OrdenesProduccion.html', {})
