"""La meta: gana la partida el primero que llega a cierta cantidad de puntos, que depende
de cuántos la empiezan (2: 26, 3: 24, 4: 22, 5: 20, 6: 20) y no cambia después."""

import pytest

from juego import puntuacion
from salas.dominio import JUGANDO, META_ALCANZADA, TERMINADA

from .ayudantes import GRIS, armar_sala, empezar_partida

USUARIOS = ['ana', 'beto', 'carla', 'dani', 'eva', 'fede']


@pytest.mark.parametrize('cuantos, meta', [(2, 26), (3, 24), (4, 22), (5, 20), (6, 20)])
def test_la_meta_depende_de_cuantos_empiezan(salas, cuantos, meta):
    codigo = armar_sala(salas, USUARIOS[:cuantos])
    salas.empezar(codigo, 'ana')

    assert salas._salas[codigo].meta == meta
    assert salas.estado(codigo, 'ana')['meta'] == meta


def test_meta_para_fuera_de_la_tabla():
    # Un lobby con uno solo muestra la de 2; nunca hay más de 6.
    assert puntuacion.meta_para(1) == 26
    assert puntuacion.meta_para(7) == 20


def test_en_el_lobby_la_meta_cambia_con_los_que_entran(salas):
    codigo = salas.crear('ana').codigo
    assert salas.estado(codigo, 'ana')['meta'] == 26

    salas.unirse(codigo, 'beto')
    salas.unirse(codigo, 'carla')
    assert salas.estado(codigo, 'ana')['meta'] == 24


def test_la_meta_queda_fija_aunque_alguien_se_vaya(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])
    salas.rendirse(codigo, 'carla')

    assert salas._salas[codigo].meta == 24
    assert salas.estado(codigo, 'ana')['meta'] == 24


def _a_un_paso(sala, usuario, puntos, primeros=0):
    """[usuario] con [puntos], y con la zona gris a una casilla de llenarse: anotando un 3
    en D1 (con los dados 1 y 3 de la primera ronda) la llena y gana 3 puntos."""
    jugador = sala.jugadores[usuario]
    jugador.puntos = puntos
    jugador.primeros = primeros
    jugador.tablero.poner('D7', 3)


def test_llegar_a_la_meta_termina_la_partida_al_cerrar_la_ronda(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    sala = salas._salas[codigo]
    _a_un_paso(sala, 'ana', 23)

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    # Todavía falta beto: los puntos se reparten al cerrar la ronda.
    assert sala.estado == JUGANDO
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    assert sala.jugadores['ana'].puntos == 26
    assert sala.estado == TERMINADA
    assert sala.motivo == META_ALCANZADA
    assert sala.ganadores == ['ana']
    assert sala.ronda == 1  # no se tiró otra ronda
    assert salas.estado(codigo, 'beto')['resultado']['motivo'] == META_ALCANZADA


def test_si_dos_llegan_en_la_misma_ronda_gana_el_de_mas_puntos(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    sala = salas._salas[codigo]
    _a_un_paso(sala, 'ana', 23)
    _a_un_paso(sala, 'beto', 24)

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    assert sala.motivo == META_ALCANZADA
    assert sala.ganadores == ['beto']  # 27 contra 26


def test_si_empatan_en_puntos_gana_el_de_mas_primeros_puestos(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    sala = salas._salas[codigo]
    _a_un_paso(sala, 'ana', 23, primeros=2)
    _a_un_paso(sala, 'beto', 23, primeros=0)

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    assert sala.ganadores == ['ana']


def test_si_empatan_en_todo_ganan_los_dos(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    sala = salas._salas[codigo]
    _a_un_paso(sala, 'ana', 23)
    _a_un_paso(sala, 'beto', 23)

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    assert sala.ganadores == ['ana', 'beto']


def test_quien_se_fue_no_termina_la_partida_aunque_pase_la_meta(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])
    sala = salas._salas[codigo]
    salas.rendirse(codigo, 'carla')
    sala.jugadores['carla'].puntos = 30

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    assert sala.estado == JUGANDO
    assert sala.ronda == 2


def test_sin_llegar_a_la_meta_la_partida_sigue(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    sala = salas._salas[codigo]
    _a_un_paso(sala, 'ana', 20)

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    assert sala.jugadores['ana'].puntos == 23
    assert sala.estado == JUGANDO
    assert sala.ronda == 2


def test_la_zona_gris_es_la_que_se_llena(salas, dados):
    """Que el ayudante haga lo que dice: la zona que llena ana es la gris, y paga 3."""
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    sala = salas._salas[codigo]
    _a_un_paso(sala, 'ana', 0)

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    assert sala.jugadores['ana'].zonas == {GRIS: (1, 1)}
    assert sala.jugadores['ana'].puntos == 3
