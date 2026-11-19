"""Los mensajes de las salas que la app muestra tal cual: cortos y sin datos de adentro
(nada de coordenadas como "D4", que el tablero no muestra)."""

import pytest

from salas.dominio import ErrorDeSala

from .ayudantes import armar_sala, empezar_preparacion


def _error(llamada) -> ErrorDeSala:
    with pytest.raises(ErrorDeSala) as capturado:
        llamada()
    return capturado.value


def test_unirse_otra_vez_a_la_misma_sala(salas):
    codigo = armar_sala(salas, ['ana', 'beto'])

    error = _error(lambda: salas.unirse(codigo, 'beto'))

    assert error.mensaje == 'Todavía estás en esa sala. Espera unos segundos.'


def test_crear_una_sala_estando_en_otra(salas):
    armar_sala(salas, ['ana', 'beto'])

    error = _error(lambda: salas.crear('beto'))

    assert error.mensaje == 'Todavía estás en otra sala. Espera unos segundos.'


def test_un_numero_que_no_cabe_en_su_casilla_no_dice_la_casilla(salas):
    codigo = empezar_preparacion(salas, ['ana', 'beto'], nivel=4)
    # En el mapa 4, E1 es de la zona naranja "4-6": el 3 no cabe.
    malo = {'E1': 3, 'C3': 1, 'F3': 2, 'A4': 4, 'E6': 5, 'B7': 6}

    error = _error(lambda: salas.preparar(codigo, 'ana', malo))

    assert error.mensaje == 'El 3 no cabe ahí.'
