"""Los puntos de las zonas y los puestos en que se llenan.

El mapa 2 tiene una zona gris de solo dos casillas (D1 y D7) que paga 3 / 2 / 1. Con el
reparto de `ayudantes.REPARTO`, con los dados (1, 3) se anota un 3 en D1 y con (2, 3), un 3
en D7; así se llena en dos rondas.
"""

import pytest

from salas.dominio import ACTIVO, SE_RINDIO, TERMINADA, Salas

from .ayudantes import GRIS, REPARTO, empezar_partida, pasar_tiempo


def _zona(salas, codigo, usuario, id_zona=GRIS):
    return next(z for z in salas.estado(codigo, usuario)['zonas'] if z['id'] == id_zona)


def _puntos(salas, codigo, quien, usuario):
    return next(j for j in salas.estado(codigo, quien)['jugadores'] if j['usuario'] == usuario)['puntos']


def _jugar_otra_cosa(salas, codigo, usuario, ronda, prohibidas=('D1', 'D7')):
    """Anota donde sea menos en [prohibidas]: para no llenar la zona gris todavía."""
    jugadas = salas.estado(codigo, usuario)['yo']['jugadas']
    for jugada in jugadas:
        for casilla in jugada['casillas']:
            if casilla not in prohibidas:
                salas.jugar(codigo, usuario, ronda, jugada['ancla'], casilla)
                return
    raise AssertionError(f'{usuario} no tiene dónde jugar fuera de {prohibidas}')


def test_el_primero_en_llenar_la_zona_gris_se_lleva_3_puntos(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))
    dados.poner(2, 3)
    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')
    dados.poner(1, 1)

    salas.jugar(codigo, 'ana', 2, 2, 'D7')  # ana llena la zona gris
    _jugar_otra_cosa(salas, codigo, 'beto', 2)

    zona = _zona(salas, codigo, 'beto')
    assert _puntos(salas, codigo, 'beto', 'ana') == 3
    assert _puntos(salas, codigo, 'beto', 'beto') == 0
    assert zona['puestos'] == [{'usuario': 'ana', 'puesto': 1, 'ronda': 2}]
    assert zona['agotada'] is False
    assert zona['puntos_siguiente'] == 2  # el segundo puesto da 2


def test_puestos_en_rondas_distintas_pagan_3_2_1_y_el_cuarto_nada(salas, dados):
    jugadores = ['ana', 'beto', 'carla', 'dani']
    codigo = empezar_partida(salas, dados, jugadores, primera_tirada=(1, 3))

    # Ronda 1: todos anotan el 3 en D1. Ronda 2 con (2, 3): solo ana llena D7.
    dados.poner(2, 3)
    for usuario in jugadores:
        salas.jugar(codigo, usuario, 1, 1, 'D1')
    dados.poner(2, 3)
    salas.jugar(codigo, 'ana', 2, 2, 'D7')
    for usuario in jugadores[1:]:
        _jugar_otra_cosa(salas, codigo, usuario, 2)
    assert _puntos(salas, codigo, 'ana', 'ana') == 3

    # Ronda 3 con (2, 3): beto la llena (segundo puesto, 2 puntos).
    dados.poner(2, 3)
    salas.jugar(codigo, 'beto', 3, 2, 'D7')
    for usuario in ['ana', 'carla', 'dani']:
        _jugar_otra_cosa(salas, codigo, usuario, 3)
    assert _puntos(salas, codigo, 'ana', 'beto') == 2
    assert _zona(salas, codigo, 'ana')['puntos_siguiente'] == 1

    # Ronda 4: carla la llena (tercer puesto, 1 punto) y la zona queda agotada.
    dados.poner(2, 3)
    salas.jugar(codigo, 'carla', 4, 2, 'D7')
    for usuario in ['ana', 'beto', 'dani']:
        _jugar_otra_cosa(salas, codigo, usuario, 4)
    zona = _zona(salas, codigo, 'ana')
    assert _puntos(salas, codigo, 'ana', 'carla') == 1
    assert zona['agotada'] is True
    assert zona['puntos_siguiente'] == 0

    # Ronda 5: dani la llena en el cuarto puesto: 0 puntos, pero queda registrado.
    dados.poner(2, 3)
    salas.jugar(codigo, 'dani', 5, 2, 'D7')
    for usuario in ['ana', 'beto', 'carla']:
        _jugar_otra_cosa(salas, codigo, usuario, 5)
    assert _puntos(salas, codigo, 'ana', 'dani') == 0
    assert [p['puesto'] for p in _zona(salas, codigo, 'ana')['puestos']] == [1, 2, 3, 4]


def test_si_dos_la_llenan_en_la_misma_ronda_los_dos_son_primeros_y_el_siguiente_es_tercero(
    salas, dados
):
    jugadores = ['ana', 'beto', 'carla']
    codigo = empezar_partida(salas, dados, jugadores, primera_tirada=(1, 3))
    dados.poner(2, 3)
    for usuario in jugadores:
        salas.jugar(codigo, usuario, 1, 1, 'D1')

    dados.poner(2, 3)
    salas.jugar(codigo, 'ana', 2, 2, 'D7')
    salas.jugar(codigo, 'beto', 2, 2, 'D7')
    _jugar_otra_cosa(salas, codigo, 'carla', 2)

    zona = _zona(salas, codigo, 'carla')
    assert [(p['usuario'], p['puesto']) for p in zona['puestos']] == [('ana', 1), ('beto', 1)]
    assert _puntos(salas, codigo, 'carla', 'ana') == _puntos(salas, codigo, 'carla', 'beto') == 3
    assert zona['puntos_siguiente'] == 1  # carla sería la tercera: el segundo puesto se salta
    vista = salas.estado(codigo, 'carla')
    assert [j['primeros'] for j in vista['jugadores']] == [1, 1, 0]


def test_los_puntos_no_se_dan_hasta_que_se_cierra_la_ronda(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'], primera_tirada=(1, 3))
    dados.poner(2, 3)
    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')
    dados.poner(1, 1)
    salas.jugar(codigo, 'ana', 2, 2, 'D7')

    # Beto todavía no jugó la ronda 2: ana aún no ve sus puntos.
    assert _puntos(salas, codigo, 'beto', 'ana') == 0
    assert _zona(salas, codigo, 'beto')['puestos'] == []


def test_quien_llena_la_zona_y_se_desconecta_en_esa_ronda_conserva_el_puesto(
    salas, reloj, dados
):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'], primera_tirada=(1, 3))
    dados.poner(2, 3)
    for usuario in ('ana', 'beto', 'carla'):
        salas.jugar(codigo, usuario, 1, 1, 'D1')
    dados.poner(1, 1)
    salas.jugar(codigo, 'carla', 2, 2, 'D7')  # carla llena la zona

    # Carla se desconecta antes de que cierre la ronda; ana y beto siguen.
    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto'], 11)
    assert salas._salas[codigo].jugadores['carla'].estado != ACTIVO
    _jugar_otra_cosa(salas, codigo, 'ana', 2)
    _jugar_otra_cosa(salas, codigo, 'beto', 2)

    assert _puntos(salas, codigo, 'ana', 'carla') == 3
    assert _zona(salas, codigo, 'ana')['puestos'][0]['usuario'] == 'carla'


def test_quien_se_rinde_conserva_los_puntos_que_ya_gano_pero_no_puede_ganar(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'], primera_tirada=(1, 3))
    dados.poner(2, 3)
    for usuario in ('ana', 'beto', 'carla'):
        salas.jugar(codigo, usuario, 1, 1, 'D1')
    dados.poner(1, 1)
    salas.jugar(codigo, 'carla', 2, 2, 'D7')  # carla (que no es la anfitriona) llena la zona
    _jugar_otra_cosa(salas, codigo, 'ana', 2)
    _jugar_otra_cosa(salas, codigo, 'beto', 2)
    assert _puntos(salas, codigo, 'ana', 'carla') == 3

    salas.rendirse(codigo, 'carla')
    salas.rendirse(codigo, 'beto')  # queda solo ana: gana, aunque carla tenía más puntos

    resultado = salas.estado(codigo, 'ana')['resultado']
    assert resultado['ganadores'] == ['ana']
    ranking = {r['usuario']: r for r in resultado['ranking']}
    assert ranking['carla']['puntos'] == 3
    assert ranking['carla']['estado'] == SE_RINDIO
    assert resultado['ranking'][0]['usuario'] == 'ana'  # los que siguen en la partida van primero


# -------- cada zona paga por separado (dos zonas del mismo color)


def _sala_nivel_1(salas, usuarios):
    from .ayudantes import armar_sala

    codigo = armar_sala(salas, usuarios, nivel=1)
    salas.empezar(codigo, usuarios[0])
    return codigo, salas._salas[codigo]


def _llenar(sala, usuario, id_zona, valor):
    """Llena una zona del tablero de [usuario] directamente (para probar los puestos sin
    jugar una partida entera)."""
    from juego.tablero import mapas

    jugador = sala.jugadores[usuario]
    zona = next(z for z in mapas()[sala.nivel].zonas if z.id == id_zona)
    for casilla in zona.casillas:
        jugador.tablero.poner(casilla, valor)


def test_las_dos_zonas_azules_del_mapa_1_pagan_7_cada_una_al_primero_que_la_llene(salas):
    # En el mapa 1 las zonas azules son la 4 y la 5.
    codigo, sala = _sala_nivel_1(salas, ['ana', 'beto'])
    _llenar(sala, 'ana', 4, 2)   # ana llena una azul
    _llenar(sala, 'beto', 5, 3)  # beto llena la otra

    salas._repartir_puestos(sala)

    assert sala.jugadores['ana'].puntos == 7
    assert sala.jugadores['beto'].puntos == 7
    assert sala.puestos[4] == [{'usuario': 'ana', 'puesto': 1, 'ronda': 0}]
    assert sala.puestos[5] == [{'usuario': 'beto', 'puesto': 1, 'ronda': 0}]


def test_llenar_la_segunda_azul_despues_de_la_primera_da_el_puesto_de_esa_zona(salas):
    codigo, sala = _sala_nivel_1(salas, ['ana', 'beto'])
    _llenar(sala, 'ana', 4, 2)
    salas._repartir_puestos(sala)
    _llenar(sala, 'beto', 4, 3)  # beto llena la MISMA zona que ana: es el segundo
    _llenar(sala, 'ana', 5, 4)   # ana llena la otra: es la primera de esa zona

    sala.ronda = 5
    salas._repartir_puestos(sala)

    assert sala.jugadores['beto'].puntos == 5          # 2.º en la azul 4
    assert sala.jugadores['ana'].puntos == 7 + 7       # 1.º en la azul 4, 1.º en la azul 5
    assert sala.jugadores['ana'].primeros == 2


def test_repartir_puestos_dos_veces_no_da_los_puntos_dos_veces(salas):
    codigo, sala = _sala_nivel_1(salas, ['ana', 'beto'])
    _llenar(sala, 'ana', 4, 2)

    salas._repartir_puestos(sala)
    salas._repartir_puestos(sala)

    assert sala.jugadores['ana'].puntos == 7
    assert len(sala.puestos[4]) == 1


@pytest.mark.parametrize(('nivel', 'zona', 'primero'), [
    (1, 1, 8),   # amarilla del mapa 1
    (2, 10, 3),  # gris del mapa 2
    (3, 8, 8),   # gris del mapa 3
    (4, 7, 6),   # naranja "4-6" del mapa 4
    (4, 8, 6),   # naranja "1-3" del mapa 4
])
def test_cada_zona_especial_paga_lo_que_dice_la_tabla(salas, nivel, zona, primero):
    from .ayudantes import armar_sala

    codigo = armar_sala(salas, ['ana', 'beto'], nivel=nivel)
    salas.empezar(codigo, 'ana')
    sala = salas._salas[codigo]
    valor = 5 if (nivel, zona) == (4, 7) else 2  # la naranja alta solo acepta 4-6
    _llenar(sala, 'ana', zona, valor)

    salas._repartir_puestos(sala)

    assert sala.jugadores['ana'].puntos == primero


# -------- el ganador y los desempates


def _con_puntos(sala, **por_jugador):
    for usuario, (puntos, primeros) in por_jugador.items():
        sala.jugadores[usuario].puntos = puntos
        sala.jugadores[usuario].primeros = primeros


def test_gana_quien_mas_puntos_suma(salas):
    codigo, sala = _sala_nivel_1(salas, ['ana', 'beto', 'carla'])
    _con_puntos(sala, ana=(10, 0), beto=(14, 0), carla=(12, 5))

    assert Salas._ganadores_por_puntos(sala) == ['beto']


def test_si_empatan_en_puntos_gana_quien_tenga_mas_primeros(salas):
    codigo, sala = _sala_nivel_1(salas, ['ana', 'beto', 'carla'])
    _con_puntos(sala, ana=(10, 1), beto=(10, 3), carla=(8, 5))

    assert Salas._ganadores_por_puntos(sala) == ['beto']


def test_si_siguen_empatados_ganan_todos_los_empatados(salas):
    codigo, sala = _sala_nivel_1(salas, ['ana', 'beto', 'carla'])
    _con_puntos(sala, ana=(10, 2), beto=(10, 2), carla=(8, 5))

    assert Salas._ganadores_por_puntos(sala) == ['ana', 'beto']


def test_los_que_quedaron_fuera_no_ganan_aunque_tengan_mas_puntos(salas):
    codigo, sala = _sala_nivel_1(salas, ['ana', 'beto', 'carla'])
    _con_puntos(sala, ana=(30, 5), beto=(10, 0), carla=(5, 0))
    sala.jugadores['ana'].estado = SE_RINDIO

    assert Salas._ganadores_por_puntos(sala) == ['beto']


def test_la_partida_terminada_por_tablero_lleno_da_los_ganadores_por_puntos(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    sala = salas._salas[codigo]
    for jugador in sala.jugadores.values():
        for casilla in jugador.tablero.casillas():
            if casilla != 'D1' and jugador.tablero.valor(casilla) is None:
                jugador.tablero.poner(casilla, 3)
    _con_puntos(sala, ana=(5, 0), beto=(9, 1))
    sala.dados = (1, 3)

    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    assert sala.estado == TERMINADA
    assert sala.ganadores == ['beto']


def test_cada_zona_dice_lo_que_paga_cada_puesto_segun_el_mapa(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    zonas = {z['id']: z for z in salas.estado(codigo, 'ana')['zonas']}

    # El mapa 2: la gris paga 3/2/1, y todas las zonas traen sus tres puestos.
    assert zonas[GRIS]['puntos_por_puesto'] == [3, 2, 1]
    for zona in zonas.values():
        assert len(zona['puntos_por_puesto']) == 3
        assert zona['puntos_siguiente'] == zona['puntos_por_puesto'][0]
