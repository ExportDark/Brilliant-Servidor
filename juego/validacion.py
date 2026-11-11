"""Qué jugadas se pueden hacer en un tablero.

Una jugada anota el número de un dado en una casilla libre, pegada (sin diagonales)
a una casilla que tenga el número del otro dado, el dado ancla, y donde la regla de
color de su zona lo permita. Es la misma regla que `lib/juego/validacion_jugada.dart`
en la app.
"""

from .reglas import puede_agregar
from .tablero import Tablero, vecinas

VALIDA = 'valida'
OCUPADA = 'ocupada'
SIN_VECINO = 'sin_vecino'
REGLA_ROTA = 'regla_rota'

CARAS = range(1, 7)


def evaluar_jugada(tablero: Tablero, casilla: str, ancla: int, valor: int) -> str:
    """Qué pasaría al anotar [valor] en [casilla] con el dado ancla en [ancla]."""
    if tablero.valor(casilla) is not None:
        return OCUPADA
    if not any(tablero.valor(v) == ancla for v in vecinas(casilla)):
        return SIN_VECINO
    zona = tablero.zona_de(casilla)
    if puede_agregar(zona.tipo, tablero.valores_de_la_zona(zona), valor):
        return VALIDA
    return REGLA_ROTA


def jugadas_legales(tablero: Tablero, ancla: int, valor: int) -> list[str]:
    """Las casillas donde se puede anotar [valor] con el ancla en [ancla]."""
    return [c for c in tablero.casillas() if evaluar_jugada(tablero, c, ancla, valor) == VALIDA]


def hay_jugada(tablero: Tablero, ancla: int, valor: int) -> bool:
    return any(evaluar_jugada(tablero, c, ancla, valor) == VALIDA for c in tablero.casillas())


def hay_jugada_posible(tablero: Tablero) -> bool:
    """Si alguna tirada posible (cualquier ancla y cualquier otro dado) tendría
    jugada. Cuando no la hay, el tablero ya no puede avanzar."""
    return any(hay_jugada(tablero, ancla, valor) for ancla in CARAS for valor in CARAS)


def acepta_como_inicial(tablero: Tablero, casilla: str, valor: int) -> bool:
    """Si [valor] cabe en [casilla] al empezar, con su zona todavía vacía. Solo una
    zona naranja ("1-3" o "4-6") puede rechazar un número."""
    return puede_agregar(tablero.zona_de(casilla).tipo, [], valor)
