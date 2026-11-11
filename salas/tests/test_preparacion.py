import pytest

from salas.dominio import (
    JUGANDO,
    PREPARANDO,
    SEGUNDOS_DE_PREPARACION,
    ErrorDeSala,
)

from .ayudantes import REPARTO, empezar_preparacion, latir, pasar_tiempo


def _error(llamada) -> ErrorDeSala:
    with pytest.raises(ErrorDeSala) as capturado:
        llamada()
    return capturado.value


def test_al_empezar_cada_jugador_tiene_un_tablero_vacio_y_sus_casillas_iniciales(salas):
    codigo = empezar_preparacion(salas, ['ana', 'beto'])

    vista = salas.estado(codigo, 'ana')

    assert vista['estado'] == PREPARANDO
    assert vista['yo']['tablero'] == {}
    assert vista['yo']['iniciales'] == ['E1', 'A3', 'C4', 'F5', 'B6', 'E7']
    assert vista['segundos_restantes'] == SEGUNDOS_DE_PREPARACION


def test_la_partida_arranca_cuando_todos_terminaron_de_repartir(salas, dados):
    codigo = empezar_preparacion(salas, ['ana', 'beto'])
    dados.poner(1, 3)

    salas.preparar(codigo, 'ana', REPARTO)
    assert salas.estado(codigo, 'ana')['estado'] == PREPARANDO
    assert salas.estado(codigo, 'ana')['jugadores'][0]['listo'] is True
    assert salas.estado(codigo, 'ana')['jugadores'][1]['listo'] is False

    salas.preparar(codigo, 'beto', REPARTO)

    vista = salas.estado(codigo, 'ana')
    assert vista['estado'] == JUGANDO
    assert vista['ronda'] == 1
    assert vista['dados'] == [1, 3]


def test_cada_jugador_puede_repartir_distinto(salas, dados):
    codigo = empezar_preparacion(salas, ['ana', 'beto'])
    otro = {'E1': 6, 'A3': 5, 'C4': 4, 'F5': 3, 'B6': 2, 'E7': 1}
    dados.poner(1, 3)

    salas.preparar(codigo, 'ana', REPARTO)
    salas.preparar(codigo, 'beto', otro)

    assert salas.estado(codigo, 'ana')['yo']['tablero'] == REPARTO
    assert salas.estado(codigo, 'beto')['yo']['tablero'] == otro


@pytest.mark.parametrize('valores', [
    None,
    [],
    'E1',
    {},
    {'E1': 1},                                                     # faltan casillas
    {**REPARTO, 'D4': 3},                                         # sobra una casilla
    {'E1': 1, 'A3': 3, 'C4': 4, 'F5': 5, 'B6': 6, 'D4': 2},      # una casilla que no es inicial
    {**REPARTO, 'E7': 1},                                         # se repite el 1
    {**REPARTO, 'E7': 7},                                         # un 7
    {**REPARTO, 'E7': 0},
    {**REPARTO, 'E7': '2'},                                       # texto
    {**REPARTO, 'E7': 2.0},                                       # decimal
    {**REPARTO, 'E7': None},
    {**REPARTO, 'E7': True},
    {**REPARTO, 'E7': [2]},
])
def test_un_reparto_que_no_es_valido_se_rechaza_y_no_cambia_nada(salas, valores):
    codigo = empezar_preparacion(salas, ['ana', 'beto'])

    error = _error(lambda: salas.preparar(codigo, 'ana', valores))

    assert (error.codigo, error.estado_http) == ('preparacion_invalida', 400)
    vista = salas.estado(codigo, 'ana')
    assert vista['yo']['tablero'] == {}
    assert vista['yo']['preparado'] is False


def test_en_el_mapa_4_las_naranjas_solo_aceptan_su_rango(salas):
    codigo = empezar_preparacion(salas, ['ana', 'beto'], nivel=4)
    # En el mapa 4, E1 es de la zona "4-6" y B7 de la "1-3".
    malo = {'E1': 3, 'C3': 1, 'F3': 2, 'A4': 4, 'E6': 5, 'B7': 6}
    bueno = {'E1': 4, 'C3': 1, 'F3': 2, 'A4': 3, 'E6': 6, 'B7': 5}
    bueno['B7'], bueno['E6'] = 1, 5
    bueno['C3'] = 6

    assert _error(lambda: salas.preparar(codigo, 'ana', malo)).detalles['motivo'] in ('zona', 'numeros')
    assert _error(lambda: salas.preparar(codigo, 'ana', {**malo, 'E1': 3, 'B7': 6})).codigo == 'preparacion_invalida'
    salas.preparar(codigo, 'ana', {'E1': 4, 'C3': 6, 'F3': 2, 'A4': 3, 'E6': 5, 'B7': 1})


def test_no_se_puede_repartir_dos_veces(salas):
    codigo = empezar_preparacion(salas, ['ana', 'beto'])
    salas.preparar(codigo, 'ana', REPARTO)

    assert _error(lambda: salas.preparar(codigo, 'ana', REPARTO)).codigo == 'ya_preparaste'


def test_no_se_puede_repartir_en_el_lobby_ni_con_la_partida_en_juego(salas, dados):
    from .ayudantes import armar_sala

    codigo = armar_sala(salas, ['ana', 'beto'])
    assert _error(lambda: salas.preparar(codigo, 'ana', REPARTO)).codigo == 'estado_incorrecto'

    salas.empezar(codigo, 'ana')
    dados.poner(1, 3)
    salas.preparar(codigo, 'ana', REPARTO)
    salas.preparar(codigo, 'beto', REPARTO)
    assert _error(lambda: salas.preparar(codigo, 'ana', REPARTO)).codigo == 'estado_incorrecto'


def test_a_los_60_segundos_se_reparte_al_azar_a_quien_no_termino(salas, reloj, dados):
    codigo = empezar_preparacion(salas, ['ana', 'beto'])
    dados.poner(1, 3)
    salas.preparar(codigo, 'ana', REPARTO)

    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_DE_PREPARACION - 1)
    assert salas.estado(codigo, 'ana')['estado'] == PREPARANDO

    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto'], 1)
    vista = salas.estado(codigo, 'beto')

    assert vista['estado'] == JUGANDO
    repartido = vista['yo']['tablero']
    assert sorted(repartido.values()) == [1, 2, 3, 4, 5, 6]
    assert set(repartido) == set(vista['yo']['iniciales'])
    assert salas.estado(codigo, 'ana')['yo']['tablero'] == REPARTO  # el de ana no cambió


def test_el_reparto_al_azar_respeta_las_zonas_naranjas(salas, reloj, dados):
    for n in range(30):
        ana, beto = f'a{n}', f'b{n}'
        codigo = empezar_preparacion(salas, [ana, beto], nivel=4)
        pasar_tiempo(salas, reloj, codigo, [ana, beto], SEGUNDOS_DE_PREPARACION)
        tablero = salas.estado(codigo, ana)['yo']['tablero']
        assert 4 <= tablero['E1'] <= 6, tablero
        assert 1 <= tablero['B7'] <= 3, tablero
        assert sorted(tablero.values()) == [1, 2, 3, 4, 5, 6]
        salas.rendirse(codigo, ana)
        salas.rendirse(codigo, beto)


def test_si_nadie_reparte_se_reparte_al_azar_a_todos(salas, reloj):
    codigo = empezar_preparacion(salas, ['ana', 'beto', 'carla'])

    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto', 'carla'], SEGUNDOS_DE_PREPARACION)

    vista = salas.estado(codigo, 'ana')
    assert vista['estado'] == JUGANDO
    for usuario in ('ana', 'beto', 'carla'):
        assert len(salas.estado(codigo, usuario)['yo']['tablero']) == 6
