from django.contrib import messages
from django.core.paginator import Paginator
from django.db import DatabaseError, IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from seguridad.decorators import permiso_accion_requerido

from .forms import EmpleadoForm
from .models import Empleado

@require_http_methods(["GET"])
@permiso_accion_requerido(codigo='ver_empleados')
def listar_empleados(request):
    search = request.GET.get('q', '').strip()
    empleados_list = Empleado.objects.select_related('estado').all().order_by('-fecha_ingreso')
    if search:
        empleados_list = empleados_list.filter(
            identificacion__icontains=search
        )
    paginator = Paginator(empleados_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    ctx = {
        'empleados': page_obj.object_list,
        'page_obj': page_obj,
        'search': search
    }
    return render(request, 'empleados/_modal_listar_Empleados.html', ctx)

@require_http_methods(["GET", "POST"])
@permiso_accion_requerido(codigo='crear_empleados')
def add_empleado(request):
    if request.method == 'POST':
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                from django.utils import timezone
                obj.fecha_ingreso = timezone.now()
                obj.save()
            except (IntegrityError, DatabaseError) as e:
                form.add_error(None, f'Error al guardar: {e}')
            else:
                messages.success(request, 'Empleado creado correctamente.')
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return listar_empleados(request)
                else:
                    return redirect('listar_empleados')
    else:
        form = EmpleadoForm()
    return render(request, 'empleados/add_Empleados.html', {'form': form})

@require_http_methods(["GET", "POST"])
@permiso_accion_requerido(codigo='editar_empleados')
def detail_empleado(request, id):
    empleado = get_object_or_404(Empleado, pk=id)
    if request.method == 'POST':
        if 'cancelar' in request.POST:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return listar_empleados(request)
            return redirect('listar_empleados')
        form = EmpleadoForm(request.POST, instance=empleado)
        if form.is_valid():
            try:
                form.save()
            except (IntegrityError, DatabaseError) as e:
                form.add_error(None, f'Error al guardar: {e}')
            else:
                messages.success(request, 'Empleado actualizado exitosamente.')
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return listar_empleados(request)
                return redirect('listar_empleados')
        return render(request, 'empleados/detail_Empleados.html', {'empleado': empleado, 'form': form})

    form = EmpleadoForm(instance=empleado)
    return render(request, 'empleados/detail_Empleados.html', {'empleado': empleado, 'form': form})

@require_http_methods(["GET", "POST"])
@permiso_accion_requerido(codigo='eliminar_empleados')
def delete_empleado(request, id):
    empleado = get_object_or_404(Empleado, pk=id)
    if request.method == 'POST':
        empleado.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        else:
            return redirect('listar_empleados')
    return render(request, 'empleados/confirm_delete_empleado.html', {'empleado': empleado})
