"""El tablero chico de los demás: cada uno ve qué casillas ocuparon los otros, nunca con
qué número, y cuál ocuparon en la última ronda. La casilla de la ronda en curso no se ve
hasta que la ronda termina."""

import json

from salas.dominio import JUGANDO, META_ALCANZADA, TERMINADA

from .ayudantes import REPARTO, empezar_partida, empezar_preparacion, pasar_tiempo

INICIALES = sorted(REPARTO)


def _de(salas, codigo, quien, usuario):
    """Lo que [quien] ve de [usuario] en la lista de jugadores."""
    return next(j for j in salas.estado(codigo, quien)['jugadores'] if j['usuario'] == usuario)


def test_en_la_preparacion_no_se_ve_ninguna_casilla_de_nadie(salas):
    codigo = empezar_preparacion(salas, ['ana', 'beto'])
    salas.preparar(codigo, 'beto', REPARTO)

    beto = _de(salas, codigo, 'ana', 'beto')

    assert beto['ocupadas'] == []
    assert beto['ultima'] is None


def test_al_empezar_se_ven_las_iniciales_ocupadas_sin_sus_numeros(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    beto = _de(salas, codigo, 'ana', 'beto')

    assert beto['ocupadas'] == INICIALES
    assert beto['ultima'] is None


def test_la_casilla_de_otro_no_se_ve_hasta_que_termina_la_ronda(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    salas.jugar(codigo, 'beto', 1, 1, 'D1')
    # beto la ve en su tablero; ana todavía no.
    assert salas.estado(codigo, 'beto')['yo']['tablero']['D1'] == 3
    assert 'D1' not in _de(salas, codigo, 'ana', 'beto')['ocupadas']

    salas.jugar(codigo, 'ana', 1, 1, 'D1')  # termina la ronda

    beto = _de(salas, codigo, 'ana', 'beto')
    assert 'D1' in beto['ocupadas']
    assert beto['ultima'] == 'D1'


def test_el_numero_de_otro_nunca_viaja(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    salas.jugar(codigo, 'beto', 1, 1, 'D1')
    salas.jugar(codigo, 'ana', 1, 1, 'D1')

    vista = salas.estado(codigo, 'ana')
    beto = next(j for j in vista['jugadores'] if j['usuario'] == 'beto')

    # Solo nombres de casilla: ningún número, ni pares casilla-número.
    assert all(isinstance(c, str) and len(c) == 2 for c in beto['ocupadas'])
    assert isinstance(beto['ultima'], str)
    assert 'tablero' not in json.dumps(vista['jugadores'])


def test_la_ultima_es_la_de_la_ronda_que_termino(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    dados.poner(2, 3)  # la ronda 2: ancla 2 (E7), un 3 en D7
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    salas.jugar(codigo, 'ana', 2, 2, 'D7')
    # La ronda 2 sigue: de ana se ve la de la ronda 1, y D7 todavía no.
    ana = _de(salas, codigo, 'beto', 'ana')
    assert ana['ultima'] == 'D1'
    assert 'D7' not in ana['ocupadas']

    salas.jugar(codigo, 'beto', 2, 2, 'D7')

    ana = _de(salas, codigo, 'beto', 'ana')
    assert ana['ultima'] == 'D7'
    assert {'D1', 'D7'} <= set(ana['ocupadas'])


def test_quien_paso_no_tiene_ultima(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    # ana no juega: a los 60 s pasa sola y la ronda termina.
    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto'], 61)

    assert salas.estado(codigo, 'ana')['ronda'] == 2
    assert _de(salas, codigo, 'beto', 'ana')['ultima'] is None
    assert _de(salas, codigo, 'ana', 'beto')['ultima'] == 'D1'


def test_el_tablero_de_quien_se_fue_queda_como_estaba(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])
    salas.rendirse(codigo, 'carla')

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    carla = _de(salas, codigo, 'ana', 'carla')
    assert carla['estado'] == 'se_rindio'
    assert carla['ocupadas'] == INICIALES


def test_al_terminar_se_ve_tambien_la_jugada_de_la_ultima_ronda(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    sala = salas._salas[codigo]
    # ana a un paso de la meta: con un 3 en D1 llena la zona gris y llega a 26.
    sala.jugadores['ana'].puntos = 23
    sala.jugadores['ana'].tablero.poner('D7', 3)

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    assert sala.estado == TERMINADA and sala.motivo == META_ALCANZADA
    ana = _de(salas, codigo, 'beto', 'ana')
    assert ana['ultima'] == 'D1'
    assert 'D1' in ana['ocupadas']


def test_la_vista_cambia_de_version_al_terminar_la_ronda(salas, dados):
    """La app pregunta con ?version=N y recibe 304 si nada cambió: al terminar la ronda la
    versión cambia, así que los tableros chicos se ponen al día."""
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    salas.jugar(codigo, 'beto', 1, 1, 'D1')
    antes = salas.estado(codigo, 'ana')['version']

    salas.jugar(codigo, 'ana', 1, 1, 'D1')

    assert salas._salas[codigo].estado == JUGANDO
    assert salas.estado(codigo, 'ana')['version'] > antes
