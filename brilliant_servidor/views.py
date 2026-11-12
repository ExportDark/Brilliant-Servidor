"""Lo que el servidor dice de sí mismo, sin sesión."""

import socket

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

# Si cambia lo que la app necesita saber del servidor, sube.
VERSION = 1


def nombre_del_servidor() -> str:
    """Cómo se presenta: "Brilliant en <nombre de la PC>", lo mismo que anuncia por mDNS
    (`servir.py`)."""
    return f'Brilliant en {socket.gethostname()}'


class QuienEres(APIView):
    """`GET /servidor/`: el nombre del servidor, para la app que lo encontró probando las
    direcciones de su red (sin mDNS) y quiere mostrarlo. No pide sesión ni dice nada
    privado."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({'nombre': nombre_del_servidor(), 'version': VERSION})
