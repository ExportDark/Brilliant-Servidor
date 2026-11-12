import socket

import pytest

pytestmark = pytest.mark.django_db


def test_el_servidor_dice_su_nombre_sin_sesion(cliente):
    respuesta = cliente.get('/servidor/')

    assert respuesta.status_code == 200
    assert respuesta.data == {'nombre': f'Brilliant en {socket.gethostname()}', 'version': 1}


def test_decir_su_nombre_no_cambia_nada_ni_acepta_otros_metodos(cliente):
    assert cliente.post('/servidor/', {}, format='json').status_code == 405
    assert cliente.delete('/servidor/').status_code == 405


def test_con_un_token_inventado_igual_contesta(cliente):
    # No pide sesión: un token malo no lo convierte en 401.
    respuesta = cliente.get('/servidor/', HTTP_AUTHORIZATION='Token ' + 'x' * 64)

    assert respuesta.status_code == 200
