"""Las reglas de Python tienen que dar lo mismo que las de la app, en Dart.

`datos/casos_de_jugadas.json` lo genera la app (`tool/exportar_para_el_servidor.dart`)
con 320 tableros de partidas simuladas, y para cada uno lo que responden sus reglas.
Si falla alguno, una regla cambió en un lado y no en el otro: hay que revisar cuál
tiene razón y volver a exportar y copiar los archivos.
"""

import json
from pathlib import Path

import pytest

from juego.tablero import Tablero, mapas
from juego.validacion import evaluar_jugada, hay_jugada

DATOS = Path(__file__).resolve().parent.parent / 'datos'
CASOS = json.loads((DATOS / 'casos_de_jugadas.json').read_text(encoding='utf-8'))['casos']


def _tablero(caso) -> Tablero:
    return Tablero(mapas()[caso['nivel']], caso['valores'])


@pytest.mark.parametrize('indice', range(len(CASOS)))
def test_cada_jugada_da_lo_mismo_que_en_la_app(indice):
    caso = CASOS[indice]
    tablero = _tablero(caso)

    for jugada in caso['jugadas']:
        obtenido = evaluar_jugada(tablero, jugada['casilla'], jugada['ancla'], jugada['valor'])
        assert obtenido == jugada['resultado'], (caso['nivel'], jugada)


@pytest.mark.parametrize('indice', range(len(CASOS)))
def test_hay_jugada_y_las_zonas_llenas_dan_lo_mismo_que_en_la_app(indice):
    caso = CASOS[indice]
    tablero = _tablero(caso)

    for clave, esperado in caso['hay_jugada'].items():
        ancla, valor = (int(n) for n in clave.split('-'))
        assert hay_jugada(tablero, ancla, valor) == esperado, (caso['nivel'], clave)
    assert tablero.zonas_llenas() == caso['zonas_llenas']


def test_los_casos_cubren_los_cuatro_resultados_y_los_cuatro_mapas():
    resultados = {j['resultado'] for caso in CASOS for j in caso['jugadas']}
    assert resultados == {'valida', 'ocupada', 'sin_vecino', 'regla_rota'}
    assert {caso['nivel'] for caso in CASOS} == {1, 2, 3, 4}
