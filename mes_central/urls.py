from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

api_apps = [
    'tipo_identificacion',
    'tipo_clientes',
    'estados_clientes',
    'estado_ordenes',
    'estado_cafe',
    'estado_inven_cafe',
    'estado_tareas',
    'clientes',
    'cafe_empaque',
    'tamano_empaque',
    'origen_cafe',
    'proceso_inven_cafe',
    'variedad_cafe',
    'variendad_inven_cafe',
    'nivel_molienda',
    'nivel_tueste',
    'zaranda_grupo',
    'log_eventos',
    'ordenes',
    'ordenes_trilla',
    'ordenes_seleccion_verde',
    'ordenes_seleccion_tostado',
    'curvas_tueste',
    'inventario_cafe',
    'seleccion_tueste',
    'tueste',
    'molienda',
    'empaques',
    'materiales',
    'reportes',
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema')), 
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

for app in api_apps:
    urlpatterns.append(path('api/v1/', include(f'{app}.urls')))

from django.contrib.auth.views import LogoutView  # noqa: E402
from core.views import dashboard_view, login_view, signup_view  # noqa: E402

urlpatterns.append(path('dashboard/', dashboard_view, name='dashboard'))
urlpatterns.append(path('login/', login_view, name='login'))
urlpatterns.append(path('signup/', signup_view, name='signup'))
urlpatterns.append(path('logout/', LogoutView.as_view(), name='logout'))
urlpatterns.append(path('', login_view, name='root_login'))
urlpatterns.append(path('', include('estado_ordenes.urls')))  # rutas HTML estado-orden (/estado-orden/listar/ etc.)
urlpatterns.append(path('', include('estado_tareas.urls')))  # rutas HTML estado-tareas (/estado-tareas/listar/ etc.)
urlpatterns.append(path('', include('estado_cafe.urls')))  # rutas HTML estado (/estado-cafe/listar/ etc.)
urlpatterns.append(path('', include('nivel_molienda.urls')))  # rutas HTML niveles molienda (/nivel-molienda/listar/ etc.)
urlpatterns.append(path('', include('origen_cafe.urls')))  # rutas HTML origen cafe (/origen-cafe/listar/ etc.)
urlpatterns.append(path('', include('proceso_inven_cafe.urls')))  # rutas HTML proceso inven cafe (/proceso-inven-cafe/listar/ etc.)
urlpatterns.append(path('', include('variendad_inven_cafe.urls')))  # rutas HTML variedad inven cafe (/variedad-inven-cafe/listar/ etc.)
urlpatterns.append(path('', include('cafe_empaque.urls')))  # rutas HTML empaque cafe (/empaque-cafe/listar/ etc.)
urlpatterns.append(path('', include('empaques.urls')))  # rutas HTML empaque (/empaque/listar/ etc.)
urlpatterns.append(path('', include('zaranda_grupo.urls')))  # rutas HTML zaranda/grupo (/zaranda-grupo/listar/ etc.)
urlpatterns.append(path('', include('tamano_empaque.urls')))  # rutas HTML tamaños empaque (/tamano-empaque/listar/ etc.)
urlpatterns.append(path('', include('ordenes.urls')))  # rutas HTML órdenes producción (/ordenes-produccion/listar/ etc.)
urlpatterns.append(path('', include('ordenes_trilla.urls')))  # rutas HTML órdenes de trilla (/ordenes-trilla/listar/ etc.)
urlpatterns.append(path('', include('ordenes_seleccion_verde.urls')))  # rutas HTML órdenes selección verde (/ordenes-seleccion-verde/listar/ etc.)
urlpatterns.append(path('', include('tueste.urls')))  # rutas HTML órdenes de tueste (/ordenes-tueste/listar/ etc.)
urlpatterns.append(path('', include('seleccion_tueste.urls')))  # rutas HTML órdenes selección tueste (/ordenes-seleccion-tueste/listar/ etc.)
urlpatterns.append(path('', include('inventario_cafe.urls')))  # rutas HTML inventario café (/inventario-cafe/listar/ etc.)
urlpatterns.append(path('', include('ordenes_seleccion_tostado.urls')))  # rutas HTML órdenes selección tostado
urlpatterns.append(path('', include('reportes.urls')))  # rutas HTML reportes (/reportes/facturacion/)
# urlpatterns.append(path('', include('molienda.urls')))  # módulo Molienda oculto en la UI
urlpatterns.append(path('', include('curvas_tueste.urls')))  # rutas HTML curvas tueste (/curvas_tueste/ etc.)
urlpatterns.append(path('usuarios/', include('usuarios.urls')))  # página Usuarios y Roles
urlpatterns.append(path('', include('clientes.urls')))  # rutas HTML clientes (/clientes/listar/ etc.)
urlpatterns.append(path('', include('empleados.urls')))  # rutas HTML empleados (/empleados/ etc.)
urlpatterns.append(path('', include('materiales.urls')))  # rutas HTML materiales (/materiales/listar/ etc.)
urlpatterns.append(path('seguridad/', include('seguridad.urls')))
