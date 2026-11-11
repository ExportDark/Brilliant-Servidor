"""Partidas enteras, simuladas: jugadores que anotan al azar donde se puede, de principio
a fin, con 2 a 6 jugadores en los 4 mapas, y con jugadores que se van a la mitad.

No prueban una regla en particular: prueban que, pase lo que pase, la partida termina, no
se rompe, las reglas de cada zona se cumplen y los puntos suman lo que dice la tabla.
"""

import random

import pytest

from juego import puntuacion
from juego.reglas import puede_agregar
from juego.tablero import mapas
from salas.dominio import (
    ACTIVO,
    JUGANDO,
    SEGUNDOS_POR_RONDA,
    TERMINADA,
    Salas,
)

from .ayudantes import DadosFalsos, RelojFalso, armar_sala, pasar_tiempo

MAXIMO_DE_RONDAS = 400


def _jugar_una_ronda(salas, codigo, activos, azar):
    """Cada jugador activo pendiente anota en una casilla legal al azar."""
    for usuario in activos:
        vista = salas.estado(codigo, usuario)
        if vista['estado'] != JUGANDO or vista['yo']['accion'] != 'pendiente':
            continue
        jugadas = [j for j in vista['yo']['jugadas'] if j['casillas']]
        assert jugadas, f'{usuario} está pendiente pero no tiene jugadas'
        jugada = azar.choice(jugadas)
        salas.jugar(codigo, usuario, vista['ronda'], jugada['ancla'], azar.choice(jugada['casillas']))


def _simular(nivel: int, cuantos: int, semilla: int, se_van: dict[int, str] | None = None):
    """Juega una partida entera. [se_van] dice en qué ronda se rinde quién."""
    azar = random.Random(semilla)
    reloj = RelojFalso()
    dados = DadosFalsos()
    dados._azar = random.Random(semilla + 1)
    salas = Salas(reloj=reloj, tirar_dado=dados, azar=random.Random(semilla + 2))
    usuarios = [f'j{n}' for n in range(1, cuantos + 1)]
    codigo = armar_sala(salas, usuarios, nivel)
    salas.empezar(codigo, usuarios[0])
    pasar_tiempo(salas, reloj, codigo, usuarios, 60)  # se reparte al azar a todos

    se_van = dict(se_van or {})
    for _ in range(MAXIMO_DE_RONDAS):
        sala = salas._salas[codigo]
        if sala.estado == TERMINADA:
            return salas, sala, usuarios
        activos = [j.usuario for j in sala.activos()]
        if sala.ronda in se_van and se_van[sala.ronda] in activos:
            salas.rendirse(codigo, se_van.pop(sala.ronda))
            continue
        _jugar_una_ronda(salas, codigo, activos, azar)
        for usuario in activos:  # que sigan conectados
            if salas._salas[codigo].estado != TERMINADA and salas._salas[codigo].jugadores[usuario].estado == ACTIVO:
                salas.estado(codigo, usuario)
    pytest.fail(f'La partida no terminó en {MAXIMO_DE_RONDAS} rondas')


def _revisar_tablero(sala, usuario):
    """Que ninguna zona del tablero de [usuario] rompa su regla."""
    jugador = sala.jugadores[usuario]
    for zona in mapas()[sala.nivel].zonas:
        valores = jugador.tablero.valores_de_la_zona(zona)
        anotados: list[int] = []
        for valor in valores:
            assert puede_agregar(zona.tipo, anotados, valor), (usuario, zona, valores)
            anotados.append(valor)


def _revisar_puntos(sala):
    """Que los puntos de cada jugador sean la suma de lo que pagan sus puestos."""
    esperado = {usuario: 0 for usuario in sala.jugadores}
    for zona in mapas()[sala.nivel].zonas:
        puestos = sala.puestos.get(zona.id, [])
        assert len({p['usuario'] for p in puestos}) == len(puestos)  # nadie dos veces
        for posicion, p in enumerate(puestos):
            # El puesto es 1 + cuántos la llenaron en una ronda anterior.
            antes = [q for q in puestos if q['ronda'] < p['ronda']]
            assert p['puesto'] == len(antes) + 1, (zona, puestos)
            esperado[p['usuario']] += puntuacion.puntos_del_puesto(sala.nivel, zona.tipo, p['puesto'])
    assert {u: j.puntos for u, j in sala.jugadores.items()} == esperado


@pytest.mark.parametrize('nivel', [1, 2, 3, 4])
@pytest.mark.parametrize('cuantos', [2, 3, 6])
def test_una_partida_entera_termina_cumple_las_reglas_y_suma_bien(nivel, cuantos):
    salas, sala, usuarios = _simular(nivel, cuantos, semilla=nivel * 100 + cuantos)

    assert sala.estado == TERMINADA
    assert sala.motivo in ('tablero_lleno', 'sin_jugadas')
    assert sala.ganadores  # alguien gana
    assert set(sala.ganadores) <= set(usuarios)
    for usuario in usuarios:
        _revisar_tablero(sala, usuario)
    _revisar_puntos(sala)
    # Todos jugaron hasta el final: cada uno llenó alguna zona, así que hay puntos.
    assert max(j.puntos for j in sala.jugadores.values()) > 0


@pytest.mark.parametrize('semilla', range(25))
def test_muchas_partidas_de_6_jugadores_con_dados_distintos_terminan_bien(semilla):
    nivel = semilla % 4 + 1
    salas, sala, usuarios = _simular(nivel, 6, semilla=1000 + semilla)

    assert sala.estado == TERMINADA
    for usuario in usuarios:
        _revisar_tablero(sala, usuario)
    _revisar_puntos(sala)
    # Al terminar, la vista de cualquiera trae el resultado y nada raro.
    for usuario in usuarios:
        vista = salas.estado(sala.codigo, usuario)
        assert len(vista['resultado']['ranking']) == 6


@pytest.mark.parametrize('semilla', range(15))
def test_partidas_en_las_que_se_rinden_jugadores_a_la_mitad_terminan_bien(semilla):
    azar = random.Random(semilla)
    usuarios = [f'j{n}' for n in range(1, 7)]
    # Se rinden 1 a 4 jugadores (no el anfitrión j1) en rondas al azar.
    quienes = azar.sample(usuarios[1:], k=azar.randint(1, 4))
    se_van = {azar.randint(1, 12) + 2 * n: u for n, u in enumerate(quienes)}

    salas, sala, _ = _simular(semilla % 4 + 1, 6, semilla=2000 + semilla, se_van=se_van)

    assert sala.estado == TERMINADA
    activos = [j for j in sala.jugadores.values() if j.estado == ACTIVO]
    assert set(sala.ganadores) <= {j.usuario for j in activos}
    assert len(sala.ganadores) >= 1
    for usuario in sala.jugadores:
        _revisar_tablero(sala, usuario)
    _revisar_puntos(sala)


def test_si_nadie_juega_nunca_la_partida_sigue_por_tiempo_sin_romperse(salas, reloj, dados):
    from .ayudantes import pasar_tiempo

    usuarios = ['ana', 'beto', 'carla']
    codigo = armar_sala(salas, usuarios)
    salas.empezar(codigo, 'ana')
    pasar_tiempo(salas, reloj, codigo, usuarios, 60)

    pasar_tiempo(salas, reloj, codigo, usuarios, SEGUNDOS_POR_RONDA * 30)

    vista = salas.estado(codigo, 'ana')
    assert vista['estado'] == JUGANDO
    assert vista['ronda'] >= 30  # cada ronda venció sola, nadie anotó nada
    assert len(vista['yo']['tablero']) == 6
