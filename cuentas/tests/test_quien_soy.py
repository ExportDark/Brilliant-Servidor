from datetime import timedelta

import pytest
from django.utils import timezone
from knox.models import AuthToken

from .conftest import con_token

pytestmark = pytest.mark.django_db


def test_sin_token_responde_401(cliente):
    assert cliente.get('/auth/users/me/').status_code == 401


def test_con_un_token_inventado_responde_401(cliente):
    respuesta = con_token(cliente, 'x' * 64).get('/auth/users/me/')

    assert respuesta.status_code == 401


def test_con_el_token_devuelve_el_usuario(cliente, cuenta_con_sesion):
    respuesta = con_token(cliente, cuenta_con_sesion).get('/auth/users/me/')

    assert respuesta.status_code == 200
    assert respuesta.data['username'] == 'ana'


def test_un_token_vencido_ya_no_sirve(cliente, cuenta_con_sesion):
    AuthToken.objects.update(expiry=timezone.now() - timedelta(minutes=1))

    respuesta = con_token(cliente, cuenta_con_sesion).get('/auth/users/me/')

    assert respuesta.status_code == 401
