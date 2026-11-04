import pytest

from .conftest import con_token, entrar

pytestmark = pytest.mark.django_db


def test_cerrar_sesion_invalida_ese_token(cliente, cuenta_con_sesion):
    con_token(cliente, cuenta_con_sesion)

    assert cliente.post('/auth/token/logout/').status_code == 204
    assert cliente.get('/auth/users/me/').status_code == 401


def test_cerrar_sesion_deja_entrar_desde_otro_aparato(cliente, cuenta_con_sesion):
    con_token(cliente, cuenta_con_sesion).post('/auth/token/logout/')
    cliente.credentials()

    respuesta = entrar(cliente)

    assert respuesta.status_code == 200
    assert con_token(cliente, respuesta.data['token']).get('/auth/users/me/').status_code == 200


def test_sin_token_no_hay_nada_que_cerrar(cliente):
    assert cliente.post('/auth/token/logout/').status_code == 401
