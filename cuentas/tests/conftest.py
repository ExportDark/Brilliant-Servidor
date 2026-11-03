"""Ayudantes compartidos por los tests del servidor."""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

# Una contraseña que pasa todos los validadores: larga, no común, no solo
# números y distinta del nombre de usuario.
CONTRASENA = 'gema-brillante-73'


@pytest.fixture(autouse=True)
def _sin_limite_heredado():
    """El límite de intentos se cuenta en la caché: se vacía en cada test para
    que un test no herede los intentos de otro."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def cliente():
    return APIClient()


def crear_cuenta(cliente, usuario='ana', contrasena=CONTRASENA, repetida=None):
    return cliente.post(
        '/auth/users/',
        {
            'username': usuario,
            'password': contrasena,
            're_password': contrasena if repetida is None else repetida,
        },
        format='json',
    )


def entrar(cliente, usuario='ana', contrasena=CONTRASENA):
    return cliente.post(
        '/auth/token/login/',
        {'username': usuario, 'password': contrasena},
        format='json',
    )


def con_token(cliente, token):
    """El cliente, mandando [token] en cada pedido, como lo hace la app."""
    cliente.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    return cliente


@pytest.fixture
def cuenta_con_sesion(cliente):
    """Una cuenta "ana" recién creada, con su sesión iniciada. Devuelve el token."""
    assert crear_cuenta(cliente).status_code == 201
    return entrar(cliente).data['token']
