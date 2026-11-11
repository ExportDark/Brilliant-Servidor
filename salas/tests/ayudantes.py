"""Ayudantes de los tests de las salas: un reloj y unos dados que decide el test, y
atajos para armar una partida."""

import random

import pytest

from salas.dominio import Salas


class RelojFalso:
    """El reloj de las salas, que solo avanza cuando el test lo dice."""

    def __init__(self):
        self.ahora = 1000.0

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


class DadosFalsos:
    """Los dados: salen primero los números que puso el test, y después, al azar con una
    semilla fija."""

    def __init__(self):
        self.cola: list[int] = []
        self._azar = random.Random(7)

    def poner(self, *caras: int) -> None:
        self.cola.extend(caras)

    def __call__(self) -> int:
        return self.cola.pop(0) if self.cola else self._azar.randint(1, 6)


# El mapa 2 (nivel 2): sus casillas iniciales son E1 A3 C4 F5 B6 E7, y su zona gris son
# D1 y D7. Con este reparto, el ancla 1 es la casilla E1 y el ancla 2 es la E7, las dos
# vecinas de las casillas grises: con los dados (1, 3) se anota un 3 en D1, y con (2, 3),
# un 3 en D7. Así se llena la zona gris, que es de solo dos casillas.
NIVEL = 2
REPARTO = {'E1': 1, 'A3': 3, 'C4': 4, 'F5': 5, 'B6': 6, 'E7': 2}
GRIS = 10  # el id de la zona gris del mapa 2


@pytest.fixture
def reloj() -> RelojFalso:
    return RelojFalso()


@pytest.fixture
def dados() -> DadosFalsos:
    return DadosFalsos()


@pytest.fixture
def salas(reloj, dados) -> Salas:
    return Salas(reloj=reloj, tirar_dado=dados, azar=random.Random(3))


def armar_sala(salas: Salas, usuarios: list[str], nivel: int = NIVEL) -> str:
    """Una sala en el lobby: el primero de [usuarios] es el anfitrión."""
    codigo = salas.crear(usuarios[0]).codigo
    for usuario in usuarios[1:]:
        salas.unirse(codigo, usuario)
    salas.elegir_mapa(codigo, usuarios[0], nivel)
    return codigo


def empezar_preparacion(salas: Salas, usuarios: list[str], nivel: int = NIVEL) -> str:
    codigo = armar_sala(salas, usuarios, nivel)
    salas.empezar(codigo, usuarios[0])
    return codigo


def empezar_partida(
    salas: Salas,
    dados: DadosFalsos,
    usuarios: list[str],
    primera_tirada: tuple[int, int] = (1, 3),
    reparto: dict[str, int] = REPARTO,
) -> str:
    """Una partida ya en juego, en la ronda 1 con [primera_tirada], con todos preparados."""
    codigo = empezar_preparacion(salas, usuarios)
    dados.poner(*primera_tirada)
    for usuario in usuarios:
        salas.preparar(codigo, usuario, reparto)
    return codigo


def latir(salas: Salas, codigo: str, usuarios: list[str]) -> None:
    """Que [usuarios] le pregunten a la sala, como hace la app cada segundo."""
    for usuario in usuarios:
        salas.estado(codigo, usuario)


def pasar_tiempo(salas: Salas, reloj: RelojFalso, codigo: str, usuarios: list[str], segundos: float) -> None:
    """Deja pasar [segundos] con [usuarios] preguntándole a la sala cada 2 segundos, como la
    app. Sin esto, un salto largo del reloj los dejaría a todos desconectados."""
    restante = segundos
    while restante > 0:
        paso = min(2.0, restante)
        reloj.avanzar(paso)
        restante -= paso
        latir(salas, codigo, usuarios)


def ronda_de(salas: Salas, codigo: str, usuario: str) -> int:
    return salas.estado(codigo, usuario)['ronda']
