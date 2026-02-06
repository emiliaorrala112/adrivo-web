import os
from pathlib import Path
import dj_database_url  
from django.conf import settings
import cloudinary.uploader
import cloudinary.api
import cloudinary

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-clave-secreta-adrivo-final'
DEBUG = False
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'cloudinary_storage',  
    'cloudinary',
    'jazzmin',                
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'inventario',            
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'adrivo_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'inventario.context_processors.info_carrito',
                'inventario.context_processors.importe_total_carrito', 
                'inventario.context_processors.cantidad_carrito',
                'inventario.context_processors.alertas_stock',
            ],
        },
    },
]

WSGI_APPLICATION = 'adrivo_project.wsgi.application'

# BASE DE DATOS INTELIGENTE (NUBE + LOCAL)
DATABASES = {
    'default': dj_database_url.config(
        # Aquí le decimos: "Si no estás en la nube, usa mi PostgreSQL local"
        default='postgresql://postgres:adrivo@127.0.0.1:5432/adrivoweb_db',
        conn_max_age=600
    )
}

AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
]

LANGUAGE_CODE = 'es-ec'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True

# ==============================================
# CONFIGURACIÓN GENERAL DE JAZZMIN
# ==============================================
# EN adrivo_project/settings.py

JAZZMIN_SETTINGS = {
    # ... (Título, Logo, Botones siguen igual) ...
    "site_title": "Adrivo R.",
    "site_header": "Adrivo R.",
    "site_brand": "Panel Adrivo",
    "site_logo": "logo_adrivo.jpg",
    "site_logo_classes": "img-circle",
    "hide_models": ["inventario.MovimientoStock"],
    
    "topmenu_links": [
        {
            "name": "Contabilidad / Ventas", 
            "url": "reporte_financiero", 
            "permissions": ["auth.view_user"]
        },
        {
            "name": "🏪 Punto de Venta (Local)", 
            "url": "punto_venta", 
            "icon": "fas fa-cash-register",
            "permissions": ["auth.view_user"]
        },
        {"name": "Ir a la Tienda Web", "url": "/", "new_window": True, "icon": "fas fa-store"},
        {"name": "Inicio", "url": "admin:index", "permissions": ["auth.view_user"]},
        
    ],

    "model_label_overrides": {
        "inventario.Categoria": "Categorías",
        "inventario.SubCategoria": "Subcategorías",
        "inventario.ControlStock": "Stock",
        "inventario.Tipo": "Tipos",
        "inventario.Marca": "Marcas",
        "inventario.Producto": "Productos",
        "inventario.Pedido": "Pedidos",
        "auth.Group": "Grupos",
        "auth.User": "Usuarios",
    },

    # === AQUÍ ESTÁ LA MAGIA DE LOS CÍRCULOS ===
    "icons": {
        "auth": "fas fa-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        
        # ÍTEMS CON ICONO ESPECÍFICO
        "inventario.Producto": "fas fa-shopping-bag",
        "inventario.Pedido": "fas fa-shopping-cart",
        "inventario.Marca": "fas fa-tag", 
        "inventario.Tipo": "fas fa-layer-group",

        # ÍTEMS QUE ESTABAN VACÍOS (AHORA CON CÍRCULOS)
        "inventario.ControlStock": "fas fa-circle",    # <--- Círculo Relleno
        "inventario.Categoria": "fas fa-circle",       # <--- Círculo Relleno
        "inventario.SubCategoria": "far fa-circle",    # <--- Círculo Vacío (para variar)
    },
    
    "custom_links": {
        "inventario": [{
            "name": "Stock", 
            "url": "admin_stock_view",  # El nombre que pusimos en urls.py
            "icon": "fas fa-chart-bar",
            "permissions": ["inventario.view_producto"]
        },
        {
                "name": "Contabilidad / Ventas", 
                "url": "reporte_financiero", 
                "icon": "fas fa-chart-line",
                "new_window": True  # ¡Truco! Esto hace que se abra en pestaña nueva para imprimir
        }]
    },

    

    "show_ui_builder": False,
    "custom_css": "css/custom_admin.css",

}
# Busca la sección JAZZMIN_UI_TWEAKS y reemplázala con esta configuración "neutra"
# para dejar que el CSS haga el trabajo pesado.

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-white",
    "accent": "accent-primary", # Usaremos nuestro propio color primario
    "navbar": "navbar-white navbar-light",
    "sidebar": "sidebar-light-primary", # Base clara para la barra lateral
    "main_bg": "#FCF5FF",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-custom", # Usaremos una clase custom en CSS
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = '/'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = 'variedades.adrivo.r@gmail.com'
EMAIL_HOST_PASSWORD = 'nvltgcyuqqdblctz' 


# =========================================================
# CONFIGURACIÓN FINAL (FIX PARA EL ERROR ROJO)
# =========================================================
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api

# 1. Rutas Web
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
LOGIN_URL = 'login'

# 2. Carpetas Físicas
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 3. Tus Llaves de Cloudinary (ESTO ES LO QUE GUARDA LAS FOTOS)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'ddawyzbgk',
    'API_KEY': '339853434156423',
    'API_SECRET': 'PGx74GnlHdSxpUudmynA2pfObv90'
}

# 4. ¡EL PARCHE! Esta línea engaña a la librería para que no de error
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# 5. La Configuración Real (Django 5)
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}