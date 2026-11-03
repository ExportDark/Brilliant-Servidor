"""Las vistas de las cuentas. Casi todo lo hacen djoser y knox: aquí solo se
ajusta lo mínimo para usarlos juntos."""

from djoser.views import UserViewSet
from knox.views import LoginView
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle


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
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'entrar'

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user = serializer.validated_data['user']
        return super().post(request, format=format)
