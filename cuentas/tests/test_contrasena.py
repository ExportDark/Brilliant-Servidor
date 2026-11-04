import pytest
from django.contrib.auth import get_user_model

from .conftest import con_token, crear_cuenta, entrar

pytestmark = pytest.mark.django_db


def test_con_espacios_al_borde_se_crea_y_se_entra_con_la_misma(cliente):
    # Antes se recortaban al crear la cuenta y no al entrar: no se podía entrar.
    contrasena = '  gema brillante 73  '

    assert crear_cuenta(cliente, contrasena=contrasena).status_code == 201

    assert entrar(cliente, contrasena=contrasena).status_code == 200
    assert entrar(cliente, contrasena=contrasena.strip()).status_code == 400


def test_con_ene_acentos_y_emoji_se_crea_y_se_entra(cliente):
    contrasena = 'piñata-mágica-💎-73'

    assert crear_cuenta(cliente, contrasena=contrasena).status_code == 201
    assert entrar(cliente, contrasena=contrasena).status_code == 200


def test_de_128_caracteres_se_acepta(cliente):
    contrasena = 'gema-brillante-73-' + 'x' * 110

    assert crear_cuenta(cliente, contrasena=contrasena).status_code == 201
    assert entrar(cliente, contrasena=contrasena).status_code == 200


def test_de_mas_de_128_caracteres_no_se_acepta_ni_al_crear_ni_al_entrar(cliente):
    larguisima = 'gema-brillante-73-' + 'x' * 111

    creada = crear_cuenta(cliente, contrasena=larguisima)
    assert creada.status_code == 400
    assert 'password' in creada.data
    assert not get_user_model().objects.exists()

    crear_cuenta(cliente)
    respuesta = entrar(cliente, contrasena='x' * 100_000)
    assert respuesta.status_code == 400
    assert 'token' not in respuesta.data


def test_con_espacios_al_borde_se_puede_borrar_la_cuenta(cliente):
    contrasena = ' gema brillante 73 '
    crear_cuenta(cliente, contrasena=contrasena)
    token = entrar(cliente, contrasena=contrasena).data['token']

    respuesta = con_token(cliente, token).delete(
        '/auth/users/me/', {'current_password': contrasena}, format='json'
    )

    assert respuesta.status_code == 204
    assert not get_user_model().objects.exists()
