import threading

import pytest

from salas.dominio import (
    COLOCO,
    PASO,
    PENDIENTE,
    SEGUNDOS_POR_RONDA,
    TABLERO_LLENO,
    TERMINADA,
    ErrorDeSala,
)

from .ayudantes import REPARTO, empezar_partida, pasar_tiempo


def _error(llamada) -> ErrorDeSala:
    with pytest.raises(ErrorDeSala) as capturado:
        llamada()
    return capturado.value


def test_todos_ven_los_mismos_dados_y_la_misma_ronda(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'], primera_tirada=(1, 3))

    vistas = [salas.estado(codigo, u) for u in ('ana', 'beto', 'carla')]

    assert {tuple(v['dados']) for v in vistas} == {(1, 3)}
    assert {v['ronda'] for v in vistas} == {1}
    assert vistas[0]['segundos_restantes'] == SEGUNDOS_POR_RONDA


def test_una_jugada_valida_anota_el_otro_dado_junto_al_ancla(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))

    # El ancla es el 1 (la casilla E1); el otro dado, un 3, va en D1, pegada a E1.
    salas.jugar(codigo, 'ana', ronda=1, dado_ancla=1, casilla='D1')

    vista = salas.estado(codigo, 'ana')
    assert vista['yo']['tablero']['D1'] == 3
    assert vista['yo']['accion'] == COLOCO
    assert vista['jugadores'][0]['listo'] is True
    assert vista['jugadores'][1]['listo'] is False
    # Beto no ve nada de lo que anotó ana.
    assert 'D1' not in salas.estado(codigo, 'beto')['yo']['tablero']


def test_la_ronda_avanza_cuando_todos_jugaron_con_dados_nuevos(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))
    dados.poner(2, 3)

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    assert salas.estado(codigo, 'ana')['ronda'] == 1  # falta beto
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    vista = salas.estado(codigo, 'ana')
    assert vista['ronda'] == 2
    assert vista['dados'] == [2, 3]
    assert vista['yo']['accion'] == PENDIENTE
    assert vista['segundos_restantes'] == SEGUNDOS_POR_RONDA


@pytest.mark.parametrize(('casilla', 'ancla', 'motivo'), [
    ('E1', 1, 'ocupada'),       # una casilla inicial
    ('G7', 1, 'sin_vecino'),    # lejos del 1
    ('D2', 1, 'sin_vecino'),    # en diagonal a E1
    ('D1', 3, 'sin_vecino'),    # junto a E1, pero el ancla pedida es el 3
])
def test_una_jugada_que_no_se_puede_se_rechaza_con_su_motivo_y_no_gasta_el_turno(
    salas, dados, casilla, ancla, motivo
):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))

    error = _error(lambda: salas.jugar(codigo, 'ana', 1, ancla, casilla))

    assert (error.codigo, error.estado_http, error.detalles['motivo']) == ('jugada_invalida', 400, motivo)
    vista = salas.estado(codigo, 'ana')
    assert vista['yo']['accion'] == PENDIENTE
    assert vista['yo']['tablero'] == REPARTO


def test_la_regla_de_color_rechaza_la_jugada(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))
    salas.jugar(codigo, 'ana', 1, 1, 'D1')  # D1 = 3, en la zona gris
    salas.jugar(codigo, 'beto', 1, 1, 'D1')
    dados.poner(2, 5)
    # (se necesita la ronda 2 ya en marcha con otros dados)
    sala = salas._salas[codigo]
    sala.dados = (2, 5)

    # D7 es gris y ya tiene un 3: la zona exige iguales, así que un 5 no cabe.
    error = _error(lambda: salas.jugar(codigo, 'ana', 2, 2, 'D7'))

    assert error.detalles['motivo'] == 'regla_rota'


@pytest.mark.parametrize('dado', [5, 0, 7, -1, '1', None, 1.5, True, [1], {}])
def test_un_dado_que_no_salio_se_rechaza(salas, dados, dado):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))

    assert _error(lambda: salas.jugar(codigo, 'ana', 1, dado, 'D1')).codigo == 'dado_invalido'


@pytest.mark.parametrize('casilla', ['Z9', 'H1', 'A8', '', None, 11, ['D1'], {}, 'd1'])
def test_una_casilla_que_no_existe_se_rechaza(salas, dados, casilla):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))

    assert _error(lambda: salas.jugar(codigo, 'ana', 1, 1, casilla)).codigo == 'casilla_invalida'


def test_jugar_dos_veces_en_la_misma_ronda_se_rechaza_doble_toque(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))
    salas.jugar(codigo, 'ana', 1, 1, 'D1')

    error = _error(lambda: salas.jugar(codigo, 'ana', 1, 1, 'D1'))

    assert (error.codigo, error.estado_http) == ('ya_jugaste', 409)
    assert salas.estado(codigo, 'ana')['yo']['tablero']['D1'] == 3


def test_el_mismo_toque_enviado_a_la_vez_solo_se_cuenta_una_vez(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))
    resultados: list[str] = []

    def tocar():
        try:
            salas.jugar(codigo, 'ana', 1, 1, 'D1')
            resultados.append('ok')
        except ErrorDeSala as error:
            resultados.append(error.codigo)

    hilos = [threading.Thread(target=tocar) for _ in range(10)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert resultados.count('ok') == 1
    assert resultados.count('ya_jugaste') == 9


def test_una_jugada_de_una_ronda_que_ya_paso_se_rechaza(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))
    dados.poner(2, 3)
    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')  # cierra la ronda 1

    error = _error(lambda: salas.jugar(codigo, 'ana', 1, 1, 'C1'))

    assert (error.codigo, error.estado_http) == ('ronda_incorrecta', 409)
    assert error.detalles['ronda_actual'] == 2


@pytest.mark.parametrize('ronda', [0, 2, 99, -1, '1', None, 1.0, True, [1]])
def test_una_ronda_que_no_es_la_actual_se_rechaza(salas, dados, ronda):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))

    if isinstance(ronda, float):
        pytest.skip('1.0 == 1 en Python; el JSON de la app manda enteros')
    assert _error(lambda: salas.jugar(codigo, 'ana', ronda, 1, 'D1')).codigo == 'ronda_incorrecta'


def test_con_jugada_posible_no_se_puede_pasar(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))

    error = _error(lambda: salas.pasar(codigo, 'ana', 1))

    assert (error.codigo, error.estado_http) == ('tienes_jugada', 409)
    assert salas.estado(codigo, 'ana')['yo']['accion'] == PENDIENTE


def test_quien_no_tiene_jugada_con_la_tirada_pasa_solo_y_los_demas_siguen(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))
    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    # Ahora el tablero de ana se llena: en la ronda siguiente no tendrá dónde anotar. El de
    # beto no.
    sala = salas._salas[codigo]
    sala.jugadores['ana'].tablero.valores = {c: 1 for c in sala.jugadores['ana'].tablero.casillas()}
    dados.poner(2, 3)
    salas.jugar(codigo, 'beto', 1, 1, 'D1')  # cierra la ronda 1 y tira la 2

    vista = salas.estado(codigo, 'ana')

    assert vista['ronda'] == 2
    assert vista['yo']['accion'] == PASO
    assert vista['yo']['jugadas'] == []
    assert _error(lambda: salas.pasar(codigo, 'ana', 2)).codigo == 'ya_jugaste'
    assert salas.estado(codigo, 'beto')['yo']['accion'] == PENDIENTE


def test_a_los_60_segundos_pasa_quien_no_jugo(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))
    dados.poner(2, 3)
    salas.jugar(codigo, 'ana', 1, 1, 'D1')

    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_POR_RONDA - 2)
    assert salas.estado(codigo, 'ana')['ronda'] == 1

    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto'], 2)

    vista = salas.estado(codigo, 'beto')
    assert vista['ronda'] == 2
    assert 'D1' not in vista['yo']['tablero']  # beto no anotó nada: pasó la ronda 1


def test_si_nadie_juega_las_rondas_siguen_pasando_cada_60_segundos(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_POR_RONDA * 3)

    assert salas.estado(codigo, 'ana')['ronda'] == 4


def test_no_se_puede_jugar_sin_partida_en_juego_ni_despues_de_terminar(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    salas.rendirse(codigo, 'beto')  # gana ana, la partida termina

    assert salas._salas[codigo].estado == TERMINADA
    assert _error(lambda: salas.jugar(codigo, 'ana', 1, 1, 'D1')).codigo == 'estado_incorrecto'
    assert _error(lambda: salas.pasar(codigo, 'ana', 1)).codigo == 'estado_incorrecto'


def test_la_partida_termina_cuando_todos_llenaron_su_tablero(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    sala = salas._salas[codigo]
    # A los dos solo les falta una casilla, la D1, junto a E1 (que tiene un 1).
    for jugador in sala.jugadores.values():
        for casilla in jugador.tablero.casillas():
            if casilla != 'D1' and jugador.tablero.valor(casilla) is None:
                jugador.tablero.poner(casilla, 3)
    # Una tirada con la que D1 todavía cabe: ancla 1 (E1), otro dado 3 (gris acepta 3).
    sala.dados = (1, 3)

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    sala = salas._salas[codigo]
    assert sala.estado == TERMINADA
    assert sala.motivo == TABLERO_LLENO
    assert salas.estado(codigo, 'ana')['resultado']['motivo'] == TABLERO_LLENO
