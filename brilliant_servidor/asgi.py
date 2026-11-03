"""El punto de entrada para uvicorn, que sirve la API con HTTPS."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brilliant_servidor.settings')

application = get_asgi_application()
