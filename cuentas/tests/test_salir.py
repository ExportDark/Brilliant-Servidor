import pytest

from .conftest import con_token, entrar

pytestmark = pytest.mark.django_db


def test_cerrar_sesion_invalida_ese_token(cliente, cuenta_con_sesion):
    con_token(cliente, cuenta_con_sesion)

    assert cliente.post('/auth/token/logout/').status_code == 204
    assert cliente.get('/auth/users/me/').status_code == 401


def test_cerrar_sesion_no_cierra_las_otras_sesiones(cliente, cuenta_con_sesion):
    # La misma cuenta, abierta en otro aparato.
    otro_token = entrar(cliente).data['token']

    con_token(cliente, cuenta_con_sesion).post('/auth/token/logout/')

    assert con_token(cliente, otro_token).get('/auth/users/me/').status_code == 200


def test_sin_token_no_hay_nada_que_cerrar(cliente):
    assert cliente.post('/auth/token/logout/').status_code == 401
