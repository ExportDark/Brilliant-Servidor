"""Los relojes de la partida en línea, en sus bordes: la ronda (60 s), la preparación
(60 s), la desconexión (10 s) y los segundos que se le muestran a cada jugador.

El reloj lo decide el test (`RelojFalso`): no se espera de verdad.
"""

import pytest

from salas.dominio import (
    DESCONECTADO,
    JUGANDO,
    PASO,
    PENDIENTE,
    PREPARANDO,
    SEGUNDOS_DE_PREPARACION,
    SEGUNDOS_PARA_DESCONECTAR,
    SEGUNDOS_POR_RONDA,
    TERMINADA,
)

from .ayudantes import REPARTO, armar_sala, empezar_partida, empezar_preparacion, latir


def _avanzar_preguntando(salas, reloj, codigo, usuarios, segundos):
    """Deja pasar [segundos] en pasos de 1 s, con [usuarios] preguntando en cada paso (como
    la app). Termina justo en el segundo pedido, sin redondear."""
    entero = int(segundos)
    for _ in range(entero):
        reloj.avanzar(1)
        latir(salas, codigo, usuarios)
    resto = segundos - entero
    if resto:
        reloj.avanzar(resto)
        latir(salas, codigo, usuarios)


# ------------------------------------------------------------------- la ronda


def test_a_los_59_9_segundos_la_ronda_sigue_y_a_los_60_pasa_a_quien_no_jugo(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_POR_RONDA - 0.1)
    assert salas.estado(codigo, 'ana')['ronda'] == 1
    assert salas.estado(codigo, 'ana')['yo']['accion'] == PENDIENTE

    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto'], 0.1)
    assert salas.estado(codigo, 'ana')['ronda'] == 2


def test_cada_ronda_empieza_con_60_segundos_aunque_la_anterior_cerrara_antes(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))
    dados.poner(2, 3)

    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto'], 25)
    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    vista = salas.estado(codigo, 'ana')
    assert vista['ronda'] == 2
    assert vista['segundos_restantes'] == SEGUNDOS_POR_RONDA


def test_los_segundos_que_se_muestran_bajan_con_el_tiempo_y_nunca_son_negativos(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto'], 17.5)
    assert salas.estado(codigo, 'ana')['segundos_restantes'] == pytest.approx(42.5)

    # En el instante en que vence, antes de que la sala se entere: 0, no negativo.
    sala = salas._salas[codigo]
    vista = salas._vista(sala, sala.jugadores['ana'], sala.limite + 5)
    assert vista['segundos_restantes'] == 0


def test_al_vencer_solo_pasa_quien_no_habia_jugado(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'], primera_tirada=(1, 3))
    dados.poner(2, 3)
    salas.jugar(codigo, 'ana', 1, 1, 'D1')

    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto', 'carla'], SEGUNDOS_POR_RONDA)

    assert salas.estado(codigo, 'ana')['yo']['tablero']['D1'] == 3  # lo de ana sigue
    for usuario in ('beto', 'carla'):
        assert 'D1' not in salas.estado(codigo, usuario)['yo']['tablero']


def test_el_que_no_juega_ni_pregunta_queda_fuera_a_los_10_s_no_se_le_pasa_la_ronda(
    salas, reloj, dados
):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])

    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_PARA_DESCONECTAR + 1)

    sala = salas._salas[codigo]
    assert sala.jugadores['carla'].estado == DESCONECTADO
    assert sala.estado == JUGANDO
    assert sala.ronda == 1  # los demás siguen en la misma ronda, con su tiempo


def test_si_todos_quedan_pasados_por_tiempo_se_tira_otra_vez_al_instante(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_POR_RONDA)

    vista = salas.estado(codigo, 'ana')
    assert vista['ronda'] == 2
    assert vista['yo']['accion'] in (PENDIENTE, PASO)
    assert vista['segundos_restantes'] == SEGUNDOS_POR_RONDA


# ------------------------------------------------------------- la preparación


def test_la_preparacion_dura_60_s_justos(salas, reloj):
    codigo = empezar_preparacion(salas, ['ana', 'beto'])

    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_DE_PREPARACION - 0.1)
    assert salas.estado(codigo, 'ana')['estado'] == PREPARANDO
    assert salas.estado(codigo, 'ana')['segundos_restantes'] == pytest.approx(0.1)

    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto'], 0.1)
    assert salas.estado(codigo, 'ana')['estado'] == JUGANDO


def test_la_ronda_1_tiene_sus_60_s_desde_que_termina_la_preparacion(salas, reloj):
    codigo = empezar_preparacion(salas, ['ana', 'beto'])
    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto'], 40)

    salas.preparar(codigo, 'ana', REPARTO)
    salas.preparar(codigo, 'beto', REPARTO)

    vista = salas.estado(codigo, 'ana')
    assert vista['estado'] == JUGANDO
    assert vista['segundos_restantes'] == SEGUNDOS_POR_RONDA


# ------------------------------------------------------- sin tiempo a la vista


def test_en_el_lobby_y_al_terminar_no_hay_cuenta_regresiva(salas, reloj, dados):
    codigo = armar_sala(salas, ['ana', 'beto'])
    assert salas.estado(codigo, 'ana')['segundos_restantes'] is None

    codigo = empezar_partida(salas, dados, ['carla', 'dani'])
    salas.rendirse(codigo, 'dani')
    vista = salas.estado(codigo, 'carla')
    assert vista['estado'] == TERMINADA
    assert vista['segundos_restantes'] is None


# --------------------------------------------------------------- desconexión


def test_10_segundos_justos_sin_preguntar_no_saca_y_10_1_si(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])

    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_PARA_DESCONECTAR)
    assert salas._salas[codigo].jugadores['carla'].estado != DESCONECTADO

    _avanzar_preguntando(salas, reloj, codigo, ['ana', 'beto'], 0.1)
    assert salas._salas[codigo].jugadores['carla'].estado == DESCONECTADO
