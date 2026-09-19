from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from seguridad.decorators import permiso_accion_requerido

from .forms import CalidadForm
from .models import Calidad


def _es_fragmento(request):
    return request.GET.get('fragment') == '1' or bool(request.headers.get('X-Fragment'))


def _volver_listado(request):
    parametros = {campo: request.POST.get(campo) for campo in ('q', 'page') if request.POST.get(campo)}
    if _es_fragmento(request):
        parametros['fragment'] = '1'
    url = reverse('calidad_listar')
    return redirect(f'{url}?{urlencode(parametros)}' if parametros else url)


@permiso_accion_requerido('calidad.view_calidad', 'ver_curvas_tueste')
def listar_calidad(request):
    consulta = request.GET.get('q', '').strip()
    registros = Calidad.objects.select_related('cliente', 'proceso')
    if consulta:
        registros = registros.filter(
            Q(orden__icontains=consulta)
            | Q(muestra_numero__icontains=consulta)
            | Q(cliente__nombre__icontains=consulta)
            | Q(cliente__apellidos__icontains=consulta)
            | Q(proceso__proceso_inven_cafe__icontains=consulta)
        )
    pagina = Paginator(registros, 10).get_page(request.GET.get('page'))
    contexto = {'items': pagina, 'page_obj': pagina, 'search': consulta}
    plantilla = 'calidad/_modal_listar.html' if _es_fragmento(request) else 'calidad/listar.html'
    return render(request, plantilla, contexto)


@require_http_methods(['GET', 'POST'])
@permiso_accion_requerido('calidad.add_calidad', 'crear_curvas_tueste')
def agregar_calidad(request):
    form = CalidadForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return _volver_listado(request)
    return render(request, 'calidad/_modal_formulario.html' if _es_fragmento(request) else 'calidad/formulario.html', {
        'form': form, 'titulo': 'Nueva muestra de laboratorio',
        'search': request.GET.get('q', ''), 'page': request.GET.get('page', ''),
        'is_fragment': _es_fragmento(request),
    })


@require_http_methods(['GET', 'POST'])
@permiso_accion_requerido('calidad.change_calidad', 'editar_curvas_tueste')
def editar_calidad(request, pk):
    registro = get_object_or_404(Calidad, pk=pk)
    form = CalidadForm(request.POST or None, instance=registro)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return _volver_listado(request)
    return render(request, 'calidad/_modal_formulario.html' if _es_fragmento(request) else 'calidad/formulario.html', {
        'form': form, 'registro': registro, 'titulo': f'Editar muestra #{registro.pk}',
        'search': request.GET.get('q', ''), 'page': request.GET.get('page', ''),
        'is_fragment': _es_fragmento(request),
    })
