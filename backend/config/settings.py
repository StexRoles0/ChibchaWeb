"""Configuración de Django para ChibchaWEB. Lee el entorno con django-environ.

Todos los valores tienen un valor por defecto de desarrollo para que funcione sin .env.
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR.parent / ".env", overwrite=False)  # opcional: si no existe, se ignora

_SECRET_KEY_DESARROLLO = "clave-solo-para-desarrollo-no-usar-en-produccion"
DEBUG = env.bool("DJANGO_DEBUG", default=True)
SECRET_KEY = env("DJANGO_SECRET_KEY", default=_SECRET_KEY_DESARROLLO if DEBUG else "")
if not DEBUG and SECRET_KEY in ("", _SECRET_KEY_DESARROLLO):
    raise ImproperlyConfigured(
        "Con DJANGO_DEBUG=False hay que definir una DJANGO_SECRET_KEY propia (no la de desarrollo)"
    )
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "backend"])

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "chibchaweb",
    "chibchaweb.tareas",  # management commands cargar_pagos, calcular_comisiones y generar_cheques (D-09)
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# PostgreSQL por DATABASE_URL. El esquema lo crea docs/schema.sql (D-03), no las migraciones.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://chibcha:chibcha123@localhost:5433/chibchaweb",
    )
}
# Sin este límite, con la BD caída cada petición tardaba ~8 s en responder el 503 (RT04).
DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = 2
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# Sesión + CSRF (D-04): mismo origen (el frontend usa proxy), cookie de sesión HttpOnly.
# La sesión va firmada en la cookie y no en la BD (D-30): con la BD caída (RT04) las peticiones siguen
# autenticadas y la API responde 503 CONTINGENCIA en vez de 500. Sin estado en el servidor no hay forma de revocarla,
# por eso dura poco (SESSION_COOKIE_AGE, 8 horas por defecto).
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=60 * 60 * 8)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG  # S-4: en producción las cookies solo viajan por HTTPS
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_HTTPONLY = False  # Angular lee la cookie y manda X-CSRFToken
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:4200", "http://127.0.0.1:4200", "http://localhost:8080"],
)

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": (
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
        "djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "djangorestframework_camel_case.parser.CamelCaseFormParser",
        "djangorestframework_camel_case.parser.CamelCaseMultiPartParser",
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
    ),
    # No se usa django.contrib.auth: los usuarios son del dominio (D-17). La autenticación por sesión y
    # la verificación de CSRF las hace chibchaweb.web.autenticacion.
    "DEFAULT_AUTHENTICATION_CLASSES": ["chibchaweb.web.autenticacion.AutenticacionSesion"],
    "EXCEPTION_HANDLER": "chibchaweb.web.errores.manejador",
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_PERMISSION_CLASSES": [],
}

# Cifrado y respaldo (RT04, D-07). La clave por defecto es solo de desarrollo (32 bytes en base64).
_CLAVE_CIFRADO_DESARROLLO = "ZGV2LWNsYXZlLWNpZnJhZG8tMzItYnl0ZXMtMDAwMDA="
CLAVE_CIFRADO = env("CLAVE_CIFRADO", default=_CLAVE_CIFRADO_DESARROLLO if DEBUG else "")
if not DEBUG and CLAVE_CIFRADO in ("", _CLAVE_CIFRADO_DESARROLLO):
    raise ImproperlyConfigured("Con DJANGO_DEBUG=False hay que definir una CLAVE_CIFRADO propia (no la de desarrollo)")
ALGORITMO_CIFRADO = env("ALGORITMO_CIFRADO", default="AES")
RUTA_RESPALDO = env("RUTA_RESPALDO", default=str(BASE_DIR / "respaldo" / "respaldo.log"))

# Integraciones externas (D-05, D-06)
# S-2: los simulados aceptan cualquier correo (`dev:<correo>`): solo con DEBUG; sin DEBUG se exigen los reales.
SIMULAR_EXTERNOS = env.bool("SIMULAR_EXTERNOS", default=DEBUG)
if not DEBUG and SIMULAR_EXTERNOS:
    raise ImproperlyConfigured(
        "Con DJANGO_DEBUG=False no se permite SIMULAR_EXTERNOS=True (los simulados aceptan cualquier identidad)"
    )
OIDC_CLIENT_ID = env("OIDC_CLIENT_ID", default="")
OIDC_CLIENT_SECRET = env("OIDC_CLIENT_SECRET", default="")
OIDC_DISCOVERY_URL = env("OIDC_DISCOVERY_URL", default="https://accounts.google.com/.well-known/openid-configuration")
OIDC_AUTHORIZATION_URL = env("OIDC_AUTHORIZATION_URL", default="https://accounts.google.com/o/oauth2/v2/auth")
OIDC_REDIRECT_URI = env("OIDC_REDIRECT_URI", default="http://localhost:4200/auth/callback")
URL_VALIDADOR_TARJETA = env("URL_VALIDADOR_TARJETA", default="")
URL_PROCESADOR_PAGOS = env("URL_PROCESADOR_PAGOS", default="")
CODIGO_COMERCIO = env("CODIGO_COMERCIO", default="CHIBCHAWEB")
URL_REGISTRADOR_DOMINIOS = env("URL_REGISTRADOR_DOMINIOS", default="")
ORIGEN_DATOS_LEGADO = env("ORIGEN_DATOS_LEGADO", default=str(BASE_DIR / "datos_legados"))

if not SIMULAR_EXTERNOS and not (OIDC_CLIENT_SECRET and OIDC_REDIRECT_URI):
    raise ImproperlyConfigured("Con SIMULAR_EXTERNOS=False hay que definir OIDC_CLIENT_SECRET y OIDC_REDIRECT_URI")
