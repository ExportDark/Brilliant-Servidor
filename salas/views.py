"""La API de las salas, bajo `/salas/`. Todas las rutas piden sesión (token de knox).

Cada pedido que cambia algo responde con lo mismo que `GET /salas/<código>/`: la sala como
la ve quien pidió, para ahorrarle a la app un viaje. Los errores salen como
`{"codigo": "...", "detail": "..."}` con el código HTTP que corresponde; `codigo` es
estable y es con lo que la app decide qué decirle al jugador.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import registro as modulo_registro
from .dominio import ErrorDeSala


def _registro():
    # Se busca cada vez, para que los tests puedan cambiar el registro.
    return modulo_registro.registro


def _datos(request) -> dict:
    """El cuerpo del pedido, si es un objeto JSON; si no, vacío (cada ruta rechaza lo que le
    falte, con su propio error)."""
    return request.data if isinstance(request.data, dict) else {}


class _VistaDeSala(APIView):
    """Base: convierte los `ErrorDeSala` en respuestas con su código HTTP."""

    def handle_exception(self, exc):
        if isinstance(exc, ErrorDeSala):
            cuerpo = {'codigo': exc.codigo, 'detail': exc.mensaje, **exc.detalles}
            return Response(cuerpo, status=exc.estado_http)
        return super().handle_exception(exc)

    @staticmethod
    def _vista(codigo: str, usuario: str) -> Response:
        return Response(_registro().estado(codigo, usuario))


class Crear(_VistaDeSala):
    def post(self, request):
        usuario = request.user.get_username()
        sala = _registro().crear(usuario)
        respuesta = self._vista(sala.codigo, usuario)
        respuesta.status_code = status.HTTP_201_CREATED
        return respuesta


class DetalleDeSala(_VistaDeSala):
    def get(self, request, codigo):
        """El estado de la sala. Con `?version=N`, responde 304 si no cambió desde esa
        versión. Preguntar cuenta como estar conectado."""
        version = request.query_params.get('version')
        version = int(version) if version is not None and version.isdigit() else None
        vista = _registro().estado(codigo, request.user.get_username(), version)
        if vista is None:
            return Response(status=status.HTTP_304_NOT_MODIFIED)
        return Response(vista)


class Unirse(_VistaDeSala):
    def post(self, request, codigo):
        usuario = request.user.get_username()
        sala = _registro().unirse(codigo, usuario)
        return self._vista(sala.codigo, usuario)


class ElegirMapa(_VistaDeSala):
    def post(self, request, codigo):
        usuario = request.user.get_username()
        sala = _registro().elegir_mapa(codigo, usuario, _datos(request).get('nivel'))
        return self._vista(sala.codigo, usuario)


class Empezar(_VistaDeSala):
    def post(self, request, codigo):
        usuario = request.user.get_username()
        sala = _registro().empezar(codigo, usuario)
        return self._vista(sala.codigo, usuario)


class Preparacion(_VistaDeSala):
    def post(self, request, codigo):
        usuario = request.user.get_username()
        sala = _registro().preparar(codigo, usuario, _datos(request).get('valores'))
        return self._vista(sala.codigo, usuario)


class Jugada(_VistaDeSala):
    def post(self, request, codigo):
        """Anotar (`dado_ancla` y `casilla`) o pasar (`pasar: true`), siempre con la `ronda`
        a la que se refiere el jugador: así un doble toque no se cuenta dos veces."""
        usuario = request.user.get_username()
        datos = _datos(request)
        if datos.get('pasar') is True:
            sala = _registro().pasar(codigo, usuario, datos.get('ronda'))
        else:
            sala = _registro().jugar(
                codigo, usuario, datos.get('ronda'), datos.get('dado_ancla'), datos.get('casilla'),
            )
        return self._vista(sala.codigo, usuario)


class Rendirse(_VistaDeSala):
    def post(self, request, codigo):
        """Salirse de la sala. En la partida responde la sala (con el resultado, si terminó).
        Al salir del lobby, quien sale ya no está en la sala y no tiene qué ver: responde 204."""
        usuario = request.user.get_username()
        sala = _registro().rendirse(codigo, usuario)
        if usuario not in sala.jugadores:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return self._vista(sala.codigo, usuario)
