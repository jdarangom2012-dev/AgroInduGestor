import os
from pathlib import Path
import sys
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-insecure-key')
DEBUG = True
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.trycloudflare.com').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', 'https://*.trycloudflare.com').split(',') if o.strip()]

# Honor proxy headers when running behind Cloudflare Tunnel
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    # Domain apps (initial batch; more will be appended)
    'tipo_identificacion.apps.TipoIdentificacionConfig',
    'tipo_clientes.apps.TipoClientesConfig',
    'estados_clientes.apps.EstadosClientesConfig',
    'estado_ordenes.apps.EstadoOrdenesConfig',
    'estado_cafe.apps.EstadoCafeConfig',
    'estado_inven_cafe.apps.EstadoInvenCafeConfig',
    'estado_tareas.apps.EstadoTareasConfig',
    'clientes.apps.ClientesConfig',
    'cafe_empaque.apps.CafeEmpaqueConfig',
    'tamano_empaque.apps.TamanoEmpaqueConfig',
    # Added batch 2
    'origen_cafe.apps.OrigenCafeConfig',
    'proceso_inven_cafe.apps.ProcesoInvenCafeConfig',
    'variedad_cafe.apps.VariedadCafeConfig',
    'variendad_inven_cafe.apps.VariendadInvenCafeConfig',
    'nivel_molienda.apps.NivelMoliendaConfig',
    'nivel_tueste.apps.NivelTuesteConfig',
    'zaranda_grupo.apps.ZarandaGrupoConfig',
    'log_eventos.apps.LogEventosConfig',
    'ordenes.apps.OrdenesConfig',
    'ordenes_trilla.apps.OrdenesTrillaConfig',
    'ordenes_seleccion_verde.apps.OrdenesSeleccionVerdeConfig',
    'ordenes_seleccion_tostado.apps.OrdenesSeleccionTostadoConfig',
    'curvas_tueste.apps.CurvasTuesteConfig',
    'inventario_cafe.apps.InventarioCafeConfig',
    'seleccion_tueste.apps.SeleccionTuesteConfig',
    'tueste.apps.TuesteConfig',
    'molienda.apps.MoliendaConfig',
    'empaques.apps.EmpaquesConfig',
    'materiales.apps.MaterialesConfig',
    'seguridad.apps.SeguridadConfig',
    'core.apps.CoreConfig',
    'reportes.apps.ReportesConfig',
    'usuarios.apps.UsuariosConfig',
    'empleados.apps.EmpleadosConfig',
    'rag.apps.RagConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.CorrelationIdMiddleware',
    'core.middleware.CurrentUserMiddleware',
]

ROOT_URLCONF = 'mes_central.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.user_groups',
            ],
        },
    },
]

WSGI_APPLICATION = 'mes_central.wsgi.application'

# Placeholder DB config; adjust with real SQL Server credentials
DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': os.getenv('DB_NAME', 'dbTostadoraCentral'),
        'USER': os.getenv('DB_USER', 'sa'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'Tostadora2026*'),
        # Double backslash in instance name if provided directly here
        'HOST': os.getenv('DB_HOST', 'WIN-BJ6FABBG7OK\TLCMAIN01'),
        'PORT': os.getenv('DB_PORT', '1433'),
        'OPTIONS': {
            'driver': os.getenv('ODBC_DRIVER', 'ODBC Driver 18 for SQL Server'),
            # Encryption / trust handled via env flags
            # For mssql-django you can also use extra_params
            'extra_params': f"TrustServerCertificate={os.getenv('DB_TRUST_CERT', 'yes')};" + ("Encrypt=yes;" if os.getenv('DB_ENCRYPT', 'no').lower() in ['1','true','yes'] else ''),
            'connection_timeout': int(os.getenv('DB_TIMEOUT', '8')),
        },
    }
}


# Dynamic fallback to SQLite for local/dev if credentials missing or flag set.
if (
    os.getenv('DB_ENGINE', 'mssql').lower() == 'sqlite'
    or os.getenv('USE_SQLITE', '0') == '1'
):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_VERSION = '1'

# Optional Redis cache
if os.getenv('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv('REDIS_URL'),
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

JAZZMIN_SETTINGS = {
    'site_title': 'AgroInduGestor Admin',
    'site_header': 'AgroInduGestor',
    'site_brand': 'AgroInduGestor',
    'welcome_sign': 'Bienvenido a AgroInduGestor',
    'copyright': 'Nautilus Tech',
    'show_sidebar': True,
    'navigation_expanded': True,
    'hide_apps': [],
    'hide_models': [],
    'order_with_respect_to': [
        'ordenes',
        'ordenes_trilla',
        'ordenes_seleccion_verde',
        'ordenes_seleccion_tostado',
        'seleccion_tueste',
        'tueste',
        'molienda',
        'curvas_tueste',
        'estado_cafe',
        'estado_inven_cafe',
        'estado_ordenes',
        'estado_tareas',
        'nivel_molienda',
        'nivel_tueste',
        'zaranda_grupo',
        'inventario_cafe',
        'cafe_empaque',
        'empaques',
        'materiales',
        'tamano_empaque',
        'proceso_inven_cafe',
        'clientes',
        'tipo_identificacion',
        'tipo_clientes',
        'estados_clientes',
        'origen_cafe',
        'variedad_cafe',
        'variendad_inven_cafe',
        'empleados',
        'usuarios',
        'auth',
        'seguridad',
        'log_eventos',
        'reportes',
        'core',
    ],
    'topmenu_links': [
        {'name': 'Produccion', 'app': 'ordenes'},
        {'name': 'Calidad', 'app': 'estado_cafe'},
        {'name': 'Inventario', 'app': 'inventario_cafe'},
        {'name': 'Maestros', 'app': 'clientes'},
        {'name': 'Administracion', 'app': 'auth'},
    ],
    'icons': {
        'auth': 'fas fa-user-shield',
        'auth.user': 'fas fa-user',
        'auth.group': 'fas fa-users',
        'clientes': 'fas fa-address-book',
        'curvas_tueste': 'fas fa-chart-line',
        'empaques': 'fas fa-box-open',
        'empleados': 'fas fa-id-badge',
        'estado_cafe': 'fas fa-mug-hot',
        'estado_inven_cafe': 'fas fa-clipboard-check',
        'estado_ordenes': 'fas fa-tasks',
        'estado_tareas': 'fas fa-list-check',
        'inventario_cafe': 'fas fa-warehouse',
        'log_eventos': 'fas fa-file-alt',
        'materiales': 'fas fa-boxes',
        'molienda': 'fas fa-blender',
        'nivel_molienda': 'fas fa-sliders-h',
        'nivel_tueste': 'fas fa-fire',
        'ordenes': 'fas fa-industry',
        'ordenes_trilla': 'fas fa-seedling',
        'ordenes_seleccion_tostado': 'fas fa-filter',
        'ordenes_seleccion_verde': 'fas fa-leaf',
        'origen_cafe': 'fas fa-map-marker-alt',
        'proceso_inven_cafe': 'fas fa-cogs',
        'reportes': 'fas fa-chart-pie',
        'seguridad': 'fas fa-shield-alt',
        'seleccion_tueste': 'fas fa-check-double',
        'tamano_empaque': 'fas fa-ruler-combined',
        'tipo_clientes': 'fas fa-user-tag',
        'tipo_identificacion': 'fas fa-id-card',
        'tueste': 'fas fa-fire-alt',
        'usuarios': 'fas fa-users-cog',
        'variedad_cafe': 'fas fa-coffee',
        'variendad_inven_cafe': 'fas fa-layer-group',
        'zaranda_grupo': 'fas fa-object-group',
    },
    'default_icon_parents': 'fas fa-folder-open',
    'default_icon_children': 'fas fa-circle',
    'related_modal_active': False,
    'show_ui_builder': False,
}

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': int(os.getenv('API_PAGE_SIZE', '25')),
    'DEFAULT_FILTER_BACKENDS': (
        'core.filters.DynamicSearchFilter',
        'core.filters.DynamicOrderingFilter',
    ),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'AgroInduGestor API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

from rest_framework.settings import api_settings  # noqa: E402

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

# Correlation ID header name
CORRELATION_ID_HEADER = 'HTTP_X_CORRELATION_ID'
APP_NAME = 'mes-la-central'
ORDER_DETALLE_CACHE_SECONDS = int(os.getenv('ORDER_DETALLE_CACHE_SECONDS', '30'))  # TTL cache para /ordenes/{id}/detalle/

# OpenAI RAG
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
OPENAI_VECTOR_STORE_ID = os.getenv('OPENAI_VECTOR_STORE_ID', '').strip()
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini').strip() or 'gpt-4.1-mini'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'correlation': {
            '()': 'core.logging.CorrelationIdFilter',
        }
    },
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            # Use 'format' (dictConfig maps it to 'fmt') to avoid ValueError
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s %(correlation_id)s %(user)s',
        },
        'console': {
            'format': '[%(asctime)s] %(levelname)s %(name)s %(correlation_id)s %(user)s: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json' if os.getenv('LOG_JSON', '0') == '1' else 'console',
            'filters': ['correlation'],
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO'
    },
}
