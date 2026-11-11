import pytest

from juego.tablero import Tablero, casilla_valida, mapas, vecinas


@pytest.mark.parametrize('nivel', [1, 2, 3, 4])
def test_las_zonas_cubren_las_49_casillas_exactamente_una_vez(nivel):
    casillas = [c for zona in mapas()[nivel].zonas for c in zona.casillas]

    assert len(casillas) == 49
    assert len(set(casillas)) == 49
    assert all(casilla_valida(c) for c in casillas)


@pytest.mark.parametrize('nivel', [1, 2, 3, 4])
def test_hay_seis_casillas_iniciales_cada_una_en_una_zona_distinta(nivel):
    tablero = Tablero.vacio(nivel)

    zonas = {tablero.zona_de(c).id for c in tablero.mapa.iniciales}

    assert len(tablero.mapa.iniciales) == 6
    assert len(zonas) == 6


def test_el_numero_de_zonas_de_cada_mapa():
    assert {nivel: len(m.zonas) for nivel, m in mapas().items()} == {1: 9, 2: 10, 3: 8, 4: 8}


def test_las_vecinas_son_arriba_abajo_izquierda_y_derecha_sin_salirse():
    assert sorted(vecinas('D4')) == ['C4', 'D3', 'D5', 'E4']
    assert sorted(vecinas('A1')) == ['A2', 'B1']
    assert sorted(vecinas('G7')) == ['F7', 'G6']
    assert sorted(vecinas('A4')) == ['A3', 'A5', 'B4']


@pytest.mark.parametrize('casilla', ['H1', 'A8', 'A0', '', 'AA', 'a1', None, 11])
def test_casillas_que_no_existen_no_son_validas(casilla):
    assert not casilla_valida(casilla)


def test_poner_y_copiar_no_se_mezclan():
    tablero = Tablero.vacio(1)
    copia = tablero.copia()

    tablero.poner('C1', 4)

    assert tablero.valor('C1') == 4
    assert copia.valor('C1') is None


def test_una_zona_esta_llena_cuando_todas_sus_casillas_tienen_numero():
    tablero = Tablero.vacio(2)
    gris = next(z for z in tablero.mapa.zonas if z.tipo == 'gris')

    tablero.poner('D1', 2)
    assert not tablero.zona_llena(gris)
    tablero.poner('D7', 2)

    assert tablero.zona_llena(gris)
    assert tablero.zonas_llenas() == [gris.id]
