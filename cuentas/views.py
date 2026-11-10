"""Las vistas de las cuentas. Casi todo lo hacen djoser y knox: aquí solo se
ajusta lo mínimo para usarlos juntos."""

import math

from django.conf import settings
from django.utils import timezone
from djoser.views import UserViewSet
from knox.models import AuthToken
from knox.views import LoginView
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .serializers import DatosParaEntrar



def sesion_en_otro_aparato(minutos: int) -> str:
    """El mensaje del 409: la cuenta tiene una sesión sin vencer en otro aparato."""
    unidad = 'minuto' if minutos == 1 else 'minutos'
    return (
        'Esta cuenta ya tiene la sesión iniciada en otro aparato. Ciérrala allá, o '
        f'espera {minutos} {unidad} si ya no la usas.'
    )


def _en_otro_aparato(minutos: int) -> Response:
    return Response(
        {'non_field_errors': [sesion_en_otro_aparato(minutos)]},
        status=status.HTTP_409_CONFLICT,
    )


class Usuarios(UserViewSet):
    """Crear la cuenta, verla y borrarla: los endpoints de djoser. Crear cuenta
    tiene un límite de intentos por IP, para que no se creen cuentas en masa."""

    def get_throttles(self):
        if self.action == 'create':
            self.throttle_scope = 'registro'
            return [ScopedRateThrottle()]
        return super().get_throttles()


class Entrar(LoginView):
    """Inicia sesión con usuario y contraseña en el cuerpo, en JSON, y devuelve
    un token de knox.

    La vista de knox, tal cual, espera que el usuario ya venga autenticado;
    esta revisa primero usuario y contraseña con el serializer de DRF, como
    indica la documentación de knox. Si están mal, responde 400 con el mismo
    mensaje exista o no el usuario, para no revelar qué cuentas existen.

    Una cuenta tiene una sola sesión: si ya tiene una sin vencer en otro
    aparato, responde 409 y dice cuántos minutos faltan para que venza. Una
    sesión vence a los `SESION_SIN_USO` sin usarse, y la entrada nueva borra las
    vencidas: así nadie queda afuera por reinstalar la app o perder el celular.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'entrar'

    def post(self, request, format=None):
        datos = DatosParaEntrar(data=request.data, context={'request': request})
        datos.is_valid(raise_exception=True)
        usuario = datos.validated_data['user']

        ahora = timezone.now()
        sesiones = AuthToken.objects.filter(user=usuario)
        # knox renueva el vencimiento cada vez que se usa el token
        # (AUTO_REFRESH), así que una sesión sin vencer es una usada hace poco.
        vigente = sesiones.filter(expiry__gt=ahora).order_by('-expiry').first()
        if vigente is not None:
            minutos = max(1, math.ceil((vigente.expiry - ahora).total_seconds() / 60))
            return _en_otro_aparato(minutos)
        sesiones.delete()

        request.user = usuario
        respuesta = super().post(request, format=format)
        if respuesta.status_code == status.HTTP_403_FORBIDDEN:
            # Dos entradas al mismo tiempo: knox responde en inglés que se pasó
            # del límite de sesiones. Es el mismo caso.
            return _en_otro_aparato(math.ceil(settings.SESION_SIN_USO.total_seconds() / 60))
        return respuesta
