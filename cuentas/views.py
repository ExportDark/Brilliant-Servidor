"""Las vistas de las cuentas. Casi todo lo hacen djoser y knox: aquí solo se
ajusta lo mínimo para usarlos juntos."""

from django.conf import settings
from django.utils import timezone
from djoser.views import UserViewSet
from knox.models import AuthToken
from knox.settings import knox_settings
from knox.views import LoginView
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .serializers import DatosParaEntrar

SESION_EN_OTRO_APARATO = (
    'Esta cuenta ya tiene la sesión iniciada en otro aparato. Ciérrala allá, o espera '
    'unos minutos si ya no la usas.'
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

    Una cuenta tiene una sola sesión activa: si se usó en otro aparato hace
    menos de `SESION_ACTIVA`, responde 409 y no entra. Una sesión sin usar
    desde antes ya no cuenta, y la entrada nueva la cierra: así nadie queda
    afuera por reinstalar la app o perder el celular.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'entrar'

    def post(self, request, format=None):
        datos = DatosParaEntrar(data=request.data, context={'request': request})
        datos.is_valid(raise_exception=True)
        usuario = datos.validated_data['user']

        sesiones = AuthToken.objects.filter(user=usuario)
        # knox renueva el vencimiento cada vez que se usa el token
        # (AUTO_REFRESH), así que vence = último uso + TOKEN_TTL.
        usada_hace_poco = timezone.now() + knox_settings.TOKEN_TTL - settings.SESION_ACTIVA
        if sesiones.filter(expiry__gt=usada_hace_poco).exists():
            return Response(
                {'non_field_errors': [SESION_EN_OTRO_APARATO]},
                status=status.HTTP_409_CONFLICT,
            )
        sesiones.delete()

        request.user = usuario
        return super().post(request, format=format)
