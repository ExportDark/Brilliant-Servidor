import pytest

from juego.tablero import Tablero
from juego.validacion import (
    OCUPADA,
    REGLA_ROTA,
    SIN_VECINO,
    VALIDA,
    acepta_como_inicial,
    evaluar_jugada,
    hay_jugada,
    hay_jugada_posible,
    jugadas_legales,
)


def test_una_jugada_valida_esta_libre_pegada_al_ancla_y_cumple_la_regla():
    tablero = Tablero.vacio(1)
    tablero.poner('C1', 4)

    # D1 es morada: libre, pegada al 4 de C1, y la morada acepta un 2.
    assert evaluar_jugada(tablero, 'D1', ancla=4, valor=2) == VALIDA


def test_una_casilla_ocupada_no_se_puede_usar():
    tablero = Tablero.vacio(1)
    tablero.poner('C1', 4)

    assert evaluar_jugada(tablero, 'C1', ancla=4, valor=2) == OCUPADA


def test_hay_que_estar_pegada_al_numero_del_ancla_sin_diagonales():
    tablero = Tablero.vacio(1)
    tablero.poner('C1', 4)

    assert evaluar_jugada(tablero, 'D2', ancla=4, valor=2) == SIN_VECINO  # diagonal
    assert evaluar_jugada(tablero, 'D1', ancla=5, valor=2) == SIN_VECINO  # otro número
    assert evaluar_jugada(tablero, 'F5', ancla=4, valor=2) == SIN_VECINO  # lejos


def test_la_regla_de_la_zona_puede_rechazar_la_jugada():
    tablero = Tablero.vacio(1)
    tablero.poner('C1', 3)  # azul: ya tiene un 3
    tablero.poner('C2', 3)  # azul, con otro 3

    # D2 es azul y está pegada a C2 (un 3): con el ancla en 3, el azul exige iguales.
    assert evaluar_jugada(tablero, 'D2', ancla=3, valor=3) == VALIDA
    assert evaluar_jugada(tablero, 'D2', ancla=3, valor=6) == REGLA_ROTA


def test_jugadas_legales_lista_todas_las_casillas_donde_cabe():
    tablero = Tablero.vacio(1)
    tablero.poner('C1', 4)

    legales = jugadas_legales(tablero, ancla=4, valor=2)

    # Las vecinas libres de C1: B1 (verde) y D1 (morada) aceptan un 2; C2 es azul, como
    # C1, y la zona azul ya tiene un 4: exige iguales.
    assert sorted(legales) == ['B1', 'D1']
    assert evaluar_jugada(tablero, 'C2', ancla=4, valor=2) == REGLA_ROTA
    assert all(evaluar_jugada(tablero, c, 4, 2) == VALIDA for c in legales)


def test_sin_ningun_numero_en_el_tablero_nadie_tiene_jugada():
    tablero = Tablero.vacio(3)

    assert not hay_jugada_posible(tablero)
    assert jugadas_legales(tablero, 1, 1) == []


def test_un_tablero_lleno_no_tiene_jugada_posible():
    tablero = Tablero.vacio(3)
    for casilla in tablero.casillas():
        tablero.poner(casilla, 1)

    assert tablero.lleno()
    assert not hay_jugada_posible(tablero)


def test_hay_jugada_coincide_con_jugadas_legales():
    tablero = Tablero.vacio(2)
    tablero.poner('A3', 6)
    tablero.poner('E1', 2)

    for ancla in range(1, 7):
        for valor in range(1, 7):
            assert hay_jugada(tablero, ancla, valor) == bool(jugadas_legales(tablero, ancla, valor))


@pytest.mark.parametrize(('casilla', 'valor', 'cabe'), [
    ('E1', 4, True), ('E1', 6, True), ('E1', 3, False),  # naranja "4-6"
    ('B7', 1, True), ('B7', 3, True), ('B7', 4, False),  # naranja "1-3"
    ('C3', 1, True), ('C3', 6, True),                     # morada: cualquiera
])
def test_las_casillas_iniciales_naranjas_solo_aceptan_su_rango(casilla, valor, cabe):
    assert acepta_como_inicial(Tablero.vacio(4), casilla, valor) == cabe
