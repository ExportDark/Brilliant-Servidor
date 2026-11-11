"""El tablero de 7×7: sus mapas, sus zonas y los números anotados.

Las casillas se nombran como en el manual: la letra es la columna (A a G) y el
número es la fila (1 a 7), así que `C1` es la columna C de la fila 1.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

FILAS = 7
COLUMNAS = 7
DATOS = Path(__file__).resolve().parent / 'datos'


@dataclass(frozen=True)
class Zona:
    id: int
    tipo: str
    casillas: tuple[str, ...]


@dataclass(frozen=True)
class Mapa:
    nivel: int
    iniciales: tuple[str, ...]
    zonas: tuple[Zona, ...]


@lru_cache(maxsize=1)
def mapas() -> dict[int, Mapa]:
    """Los 4 mapas oficiales, por nivel, tal como los exportó la app."""
    datos = json.loads((DATOS / 'mapas.json').read_text(encoding='utf-8'))
    return {
        m['nivel']: Mapa(
            nivel=m['nivel'],
            iniciales=tuple(m['iniciales']),
            zonas=tuple(Zona(z['id'], z['tipo'], tuple(z['casillas'])) for z in m['zonas']),
        )
        for m in datos['mapas']
    }


def casilla_valida(casilla: str) -> bool:
    return (
        isinstance(casilla, str)
        and len(casilla) == 2
        and casilla[0] in 'ABCDEFG'
        and casilla[1] in '1234567'
    )


def vecinas(casilla: str) -> list[str]:
    """Las casillas pegadas a [casilla]: arriba, abajo, izquierda y derecha. Sin
    diagonales, y sin las que caen fuera del tablero."""
    columna = ord(casilla[0]) - ord('A')
    fila = int(casilla[1]) - 1
    encontradas = []
    for f, c in ((fila - 1, columna), (fila + 1, columna), (fila, columna - 1), (fila, columna + 1)):
        if 0 <= f < FILAS and 0 <= c < COLUMNAS:
            encontradas.append(f'{chr(ord("A") + c)}{f + 1}')
    return encontradas


class Tablero:
    """Un tablero de un mapa, con los números anotados hasta ahora."""

    def __init__(self, mapa: Mapa, valores: dict[str, int] | None = None):
        self.mapa = mapa
        self.valores: dict[str, int] = dict(valores or {})
        self._zona_de = {casilla: zona for zona in mapa.zonas for casilla in zona.casillas}

    @classmethod
    def vacio(cls, nivel: int) -> 'Tablero':
        return cls(mapas()[nivel])

    def copia(self) -> 'Tablero':
        return Tablero(self.mapa, self.valores)

    def zona_de(self, casilla: str) -> Zona:
        return self._zona_de[casilla]

    def casillas(self) -> list[str]:
        return list(self._zona_de)

    def valor(self, casilla: str) -> int | None:
        return self.valores.get(casilla)

    def poner(self, casilla: str, valor: int) -> None:
        self.valores[casilla] = valor

    def valores_de_la_zona(self, zona: Zona) -> list[int]:
        return [self.valores[c] for c in zona.casillas if c in self.valores]

    def zona_llena(self, zona: Zona) -> bool:
        return all(c in self.valores for c in zona.casillas)

    def zonas_llenas(self) -> list[int]:
        return [zona.id for zona in self.mapa.zonas if self.zona_llena(zona)]

    def lleno(self) -> bool:
        return len(self.valores) == FILAS * COLUMNAS
