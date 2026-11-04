"""Iniciar sesión sin distinguir mayúsculas: "ANA" entra a la cuenta "ana"."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class SinDistinguirMayusculas(ModelBackend):
    """Busca la cuenta sin distinguir mayúsculas y deja el resto al
    `ModelBackend` de Django. Así se conserva su protección: con un usuario
    que no existe igual calcula un hash, para que el tiempo de respuesta no
    delate qué cuentas existen."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is not None:
            cuenta = get_user_model()._default_manager.filter(username__iexact=username).first()
            if cuenta is not None:
                username = cuenta.get_username()
        return super().authenticate(request, username=username, password=password, **kwargs)
