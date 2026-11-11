"""Nadie ve los números ni las casillas de los demás: solo el servidor.

Cada jugador recibe su propio tablero y sus jugadas legales. De los demás, solo lo
público: nombre, estado, si ya jugó la ronda, sus puntos y qué zonas llenó.
"""

import json

from salas.dominio import TERMINADA

from .ayudantes import empezar_partida, empezar_preparacion

# Lo único que puede decir la vista de cada uno de los otros jugadores.
CLAVES_PUBLICAS_DE_UN_JUGADOR = {'usuario', 'estado', 'anfitrion', 'listo', 'puntos', 'primeros', 'zonas'}
CLAVES_DE_UNA_ZONA = {'id', 'tipo', 'color', 'casillas', 'puestos', 'agotada', 'puntos_siguiente'}


def _tableros_en(vista) -> int:
    """Cuántos objetos "tablero" hay en la vista, a cualquier profundidad."""
    return json.dumps(vista).count('"tablero"')


def test_la_vista_solo_trae_el_tablero_de_quien_pregunta(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    for usuario in ('ana', 'beto', 'carla'):
        vista = salas.estado(codigo, usuario)
        assert _tableros_en(vista) == 1, usuario
        assert vista['yo']['usuario'] == usuario


def test_lo_que_anota_otro_no_aparece_en_mi_vista(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    antes = salas.estado(codigo, 'ana')['yo']

    salas.jugar(codigo, 'beto', 1, 1, 'D1')  # beto anota un 3 en D1

    despues = salas.estado(codigo, 'ana')['yo']
    assert despues['tablero'] == antes['tablero']
    assert 'D1' not in despues['tablero']
    assert despues['jugadas'] == antes['jugadas']


def test_de_los_otros_jugadores_solo_se_ve_lo_publico(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])
    salas.jugar(codigo, 'beto', 1, 1, 'D1')

    vista = salas.estado(codigo, 'ana')

    for jugador in vista['jugadores']:
        assert set(jugador) == CLAVES_PUBLICAS_DE_UN_JUGADOR
        assert isinstance(jugador['zonas'], list)  # ids de zonas, sin casillas ni números


def test_el_panel_de_zonas_es_publico_pero_no_tiene_numeros_de_nadie(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    salas.jugar(codigo, 'ana', 1, 1, 'D1')

    for usuario in ('ana', 'beto'):
        zonas = salas.estado(codigo, usuario)['zonas']
        assert [set(z) for z in zonas] == [CLAVES_DE_UNA_ZONA] * 10
        # Las casillas de una zona son la forma del mapa (igual para todos): son
        # nombres de casilla, no números anotados.
        for zona in zonas:
            assert all(isinstance(c, str) for c in zona['casillas'])


def test_las_jugadas_legales_son_solo_mias(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    vista = salas.estado(codigo, 'ana')

    assert 'jugadas' in vista['yo']
    assert all('jugadas' not in j for j in vista['jugadores'])


def test_en_la_preparacion_nadie_ve_el_reparto_de_los_demas(salas, dados):
    codigo = empezar_preparacion(salas, ['ana', 'beto'])
    from .ayudantes import REPARTO

    dados.poner(1, 3)
    salas.preparar(codigo, 'ana', {**REPARTO, 'E1': 6, 'B6': 1})

    vista = salas.estado(codigo, 'beto')

    assert vista['yo']['tablero'] == {}
    assert _tableros_en(vista) == 1
    assert [j['listo'] for j in vista['jugadores']] == [True, False]  # solo se sabe que ya repartió


def test_al_terminar_el_resultado_trae_puntos_y_no_tableros(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    salas.rendirse(codigo, 'beto')

    vista = salas.estado(codigo, 'ana')

    assert vista['estado'] == TERMINADA
    assert set(vista['resultado']) == {'motivo', 'ganadores', 'ranking'}
    for fila in vista['resultado']['ranking']:
        assert set(fila) == {'usuario', 'estado', 'puntos', 'primeros'}
    assert _tableros_en(vista) == 1  # solo el mío, como siempre


def test_quien_no_esta_en_la_sala_no_ve_nada(salas, dados):
    import pytest

    from salas.dominio import ErrorDeSala

    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    with pytest.raises(ErrorDeSala) as error:
        salas.estado(codigo, 'espia')

    assert error.value.codigo == 'no_eres_parte'
