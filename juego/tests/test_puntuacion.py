import pytest

from juego.puntuacion import agotada, color_de, puesto_que_sigue, puntos_del_puesto
from juego.tablero import mapas

# La tabla tal como la escribió el dueño del juego: azul, verde, rojo, morado, amarillo,
# gris y naranja, de cada mapa.
ESPERADA = {
    1: {'azul': (7, 5, 3), 'verde': (4, 3, 2), 'rojo': (6, 4, 2), 'morado': (6, 4, 2),
        'amarillo': (8, 6, 4)},
    2: {'amarillo': (6, 4, 2), 'morado': (6, 4, 2), 'rojo': (6, 4, 2), 'azul': (7, 5, 3),
        'verde': (4, 3, 2), 'gris': (3, 2, 1)},
    3: {'morado': (7, 5, 3), 'rojo': (6, 4, 2), 'azul': (7, 5, 3), 'verde': (6, 5, 4),
        'gris': (8, 6, 4), 'amarillo': (7, 5, 3)},
    4: {'morado': (7, 5, 3), 'azul': (8, 6, 4), 'rojo': (6, 4, 2), 'naranja': (6, 4, 3),
        'amarillo': (8, 6, 4), 'verde': (3, 2, 1)},
}


@pytest.mark.parametrize('nivel', [1, 2, 3, 4])
def test_la_tabla_de_cada_mapa_es_la_que_se_pidio(nivel):
    for color, puntos in ESPERADA[nivel].items():
        assert tuple(puntos_del_puesto(nivel, color, p) for p in (1, 2, 3)) == puntos, (nivel, color)


@pytest.mark.parametrize('nivel', [1, 2, 3, 4])
def test_toda_zona_de_cada_mapa_tiene_puntos(nivel):
    for zona in mapas()[nivel].zonas:
        assert puntos_del_puesto(nivel, zona.tipo, 1) > 0, (nivel, zona)


@pytest.mark.parametrize('nivel', [1, 2, 3, 4])
def test_el_mapa_no_tiene_colores_que_no_estan_en_la_tabla(nivel):
    colores = {color_de(z.tipo) for z in mapas()[nivel].zonas}
    assert colores == set(ESPERADA[nivel])


def test_del_cuarto_puesto_en_adelante_no_da_puntos():
    assert [puntos_del_puesto(1, 'azul', p) for p in (4, 5, 6, 10)] == [0, 0, 0, 0]


def test_las_dos_zonas_naranjas_pagan_igual():
    assert puntos_del_puesto(4, 'naranja_bajo', 1) == puntos_del_puesto(4, 'naranja_alto', 1) == 6


def test_un_color_que_el_mapa_no_tiene_es_un_error_no_un_cero():
    with pytest.raises(ValueError):
        puntos_del_puesto(1, 'gris', 1)  # el mapa 1 no tiene zonas grises
    with pytest.raises(ValueError):
        puntos_del_puesto(4, 'gris', 1)


def test_un_puesto_menor_que_uno_es_un_error():
    with pytest.raises(ValueError):
        puntos_del_puesto(1, 'azul', 0)


def test_el_puesto_cuenta_personas_asi_que_dos_primeros_dejan_al_tercero():
    assert puesto_que_sigue(0) == 1
    assert puesto_que_sigue(1) == 2
    assert puesto_que_sigue(2) == 3  # dos primeros
    assert puesto_que_sigue(3) == 4


def test_una_zona_con_tres_puestos_tomados_esta_agotada():
    assert [agotada(n) for n in range(5)] == [False, False, False, True, True]
