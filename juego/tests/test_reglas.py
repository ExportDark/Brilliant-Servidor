import pytest

from juego.reglas import TIPOS, puede_agregar
from juego.tablero import mapas


@pytest.mark.parametrize('tipo', ['amarillo', 'rojo'])
def test_amarillo_y_rojo_no_repiten(tipo):
    assert puede_agregar(tipo, [], 3)
    assert puede_agregar(tipo, [1, 2], 3)
    assert not puede_agregar(tipo, [1, 3], 3)


def test_verde_acepta_cualquiera():
    assert all(puede_agregar('verde', [1, 2, 3, 4, 5, 6, 6], n) for n in range(1, 7))


def test_morado_acepta_como_mucho_dos_numeros_distintos():
    assert puede_agregar('morado', [], 1)
    assert puede_agregar('morado', [1, 1, 1], 1)
    assert puede_agregar('morado', [1, 1], 2)
    assert puede_agregar('morado', [1, 2, 2], 1)
    assert not puede_agregar('morado', [1, 2], 3)


@pytest.mark.parametrize('tipo', ['azul', 'gris'])
def test_azul_y_gris_son_todos_iguales(tipo):
    assert puede_agregar(tipo, [], 5)
    assert puede_agregar(tipo, [4, 4], 4)
    assert not puede_agregar(tipo, [4, 4], 5)


def test_naranja_solo_acepta_su_rango_aunque_la_zona_este_vacia():
    assert [n for n in range(1, 7) if puede_agregar('naranja_bajo', [], n)] == [1, 2, 3]
    assert [n for n in range(1, 7) if puede_agregar('naranja_alto', [], n)] == [4, 5, 6]


def test_un_tipo_desconocido_no_se_acepta_en_silencio():
    with pytest.raises(ValueError):
        puede_agregar('dorado', [], 1)


def test_todos_los_tipos_de_los_mapas_tienen_regla():
    usados = {zona.tipo for mapa in mapas().values() for zona in mapa.zonas}

    assert usados <= set(TIPOS)
    for tipo in usados:
        puede_agregar(tipo, [], 1)
