"""Configuración del servidor de cuentas de Brilliant.

Las cuentas son las de Django (usuario y contraseña), con las contraseñas en
Argon2id. djoser da los endpoints para crear, ver y borrar la cuenta, y
django-rest-knox los tokens de sesión, que se guardan con hash y vencen.
"""

import os
import secrets
from datetime import timedelta
from pathlib import Path

from red_local import ips_de_esta_pc

BASE_DIR = Path(__file__).resolve().parent.parent


def _clave_secreta() -> str:
    """La SECRET_KEY de Django. Sale de la variable de entorno o del archivo
    `.env`; si no hay ninguna, se genera una y se guarda en `.env`, que no se
    sube al repo."""
    if clave := os.environ.get('BRILLIANT_SECRET_KEY'):
        return clave

    archivo = BASE_DIR / '.env'
    if archivo.exists():
        for linea in archivo.read_text(encoding='utf-8').splitlines():
            nombre, _, valor = linea.partition('=')
            if nombre.strip() == 'BRILLIANT_SECRET_KEY' and valor.strip():
                return valor.strip()

    clave = secrets.token_urlsafe(50)
    archivo.write_text(f'BRILLIANT_SECRET_KEY={clave}\n', encoding='utf-8')
    return clave


SECRET_KEY = _clave_secreta()

DEBUG = os.environ.get('BRILLIANT_DEBUG') == '1'

# localhost para la PC y la versión web, 10.0.2.2 para el emulador de Android
# y las IPs de la red local para el celular. Se leen al arrancar: si la PC
# cambia de red, hay que volver a levantar el servidor.
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '10.0.2.2', *ips_de_esta_pc()]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',
    'knox',
    'djoser',
    'corsheaders',
    'cuentas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'brilliant_servidor.urls'

ASGI_APPLICATION = 'brilliant_servidor.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Argon2id primero: es el que se usa para toda contraseña nueva. PBKDF2 queda
# solo para poder leer una contraseña vieja, si la hubiera.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Los mensajes de error (contraseña muy corta, usuario repetido...) salen en
# español, y la app los muestra tal cual.
LANGUAGE_CODE = 'es'
USE_I18N = True
TIME_ZONE = 'UTC'
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ('knox.auth.TokenAuthentication',),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    # Solo JSON: sin la página navegable de DRF.
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
    # Límite de intentos por IP, para que no se puedan probar contraseñas a
    # lo bruto ni crear cuentas en masa.
    'DEFAULT_THROTTLE_RATES': {
        'entrar': '5/min',
        'registro': '10/hour',
    },
}

REST_KNOX = {
    # La sesión dura 7 días y se renueva cada vez que se usa.
    'TOKEN_TTL': timedelta(days=7),
    'AUTO_REFRESH': True,
    'TOKEN_LIMIT_PER_USER': 10,
}

DJOSER = {
    # Al crear la cuenta, la contraseña se escribe dos veces.
    'USER_CREATE_PASSWORD_RETYPE': True,
    # Los tokens los da knox, no el modelo de tokens de DRF.
    'TOKEN_MODEL': None,
    # Nadie puede ver ni tocar la cuenta de otro.
    'HIDE_USERS': True,
}

# La versión web de la app se sirve desde localhost: es el único origen que
# puede llamar a la API desde un navegador.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^http://localhost:\d+$',
    r'^http://127\.0\.0\.1:\d+$',
]
