import pytest
from django.contrib.auth import get_user_model
from knox.models import AuthToken

from .conftest import CONTRASENA, con_token, entrar

pytestmark = pytest.mark.django_db


def _borrar(cliente, token, **datos):
    return con_token(cliente, token).delete('/auth/users/me/', datos, format='json')


def test_sin_la_contrasena_no_la_borra(cliente, cuenta_con_sesion):
    respuesta = _borrar(cliente, cuenta_con_sesion)

    assert respuesta.status_code == 400
    assert get_user_model().objects.filter(username='ana').exists()


def test_con_una_contrasena_mala_no_la_borra(cliente, cuenta_con_sesion):
    respuesta = _borrar(cliente, cuenta_con_sesion, current_password='no-es-la-buena-1')

    assert respuesta.status_code == 400
    assert 'current_password' in respuesta.data
    assert get_user_model().objects.filter(username='ana').exists()


def test_sin_sesion_no_se_puede_borrar(cliente, cuenta_con_sesion):
    cliente.credentials()

    respuesta = cliente.delete('/auth/users/me/', {'current_password': CONTRASENA}, format='json')

    assert respuesta.status_code == 401
    assert get_user_model().objects.filter(username='ana').exists()


def test_con_la_contrasena_la_borra_con_sus_sesiones(cliente, cuenta_con_sesion):
    otro_token = entrar(cliente).data['token']

    respuesta = _borrar(cliente, cuenta_con_sesion, current_password=CONTRASENA)

    assert respuesta.status_code == 204
    assert not get_user_model().objects.filter(username='ana').exists()
    assert not AuthToken.objects.exists()
    # Ni sus tokens viejos ni su contraseña sirven ya.
    assert con_token(cliente, otro_token).get('/auth/users/me/').status_code == 401
    cliente.credentials()
    assert entrar(cliente).status_code == 400
