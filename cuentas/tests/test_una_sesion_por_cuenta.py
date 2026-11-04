from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from knox.models import AuthToken
from knox.settings import CONSTANTS, knox_settings

from cuentas.views import SESION_EN_OTRO_APARATO

from .conftest import con_token, crear_cuenta, entrar

pytestmark = pytest.mark.django_db


def _sin_usar_desde_hace(token, tiempo):
    """Como si el aparato de [token] no lo hubiera usado desde hace [tiempo]:
    knox renueva el vencimiento en cada uso, así que vence = último uso + TTL."""
    actualizados = AuthToken.objects.filter(
        token_key=token[: CONSTANTS.TOKEN_KEY_LENGTH]
    ).update(expiry=timezone.now() - tiempo + knox_settings.TOKEN_TTL)
    assert actualizados == 1


def test_con_la_sesion_activa_en_otro_aparato_no_deja_entrar(cliente, cuenta_con_sesion):
    cliente.credentials()

    respuesta = entrar(cliente)

    assert respuesta.status_code == 409
    assert respuesta.data['non_field_errors'] == [SESION_EN_OTRO_APARATO]
    assert 'token' not in respuesta.data
    # La sesión del otro aparato sigue igual.
    assert con_token(cliente, cuenta_con_sesion).get('/auth/users/me/').status_code == 200


def test_tampoco_con_otras_mayusculas(cliente, cuenta_con_sesion):
    cliente.credentials()

    assert entrar(cliente, usuario='ANA').status_code == 409


def test_con_la_contrasena_mala_no_dice_nada_de_la_sesion(cliente, cuenta_con_sesion):
    cliente.credentials()

    respuesta = entrar(cliente, contrasena='no-es-la-buena-1')

    assert respuesta.status_code == 400
    assert SESION_EN_OTRO_APARATO not in str(respuesta.data)


def test_cerrada_en_el_otro_aparato_deja_entrar(cliente, cuenta_con_sesion):
    con_token(cliente, cuenta_con_sesion).post('/auth/token/logout/')
    cliente.credentials()

    assert entrar(cliente).status_code == 200


def test_sin_usar_desde_hace_mas_de_un_rato_la_entrada_nueva_la_cierra(cliente, cuenta_con_sesion):
    _sin_usar_desde_hace(cuenta_con_sesion, settings.SESION_ACTIVA + timedelta(minutes=1))
    cliente.credentials()

    respuesta = entrar(cliente)

    assert respuesta.status_code == 200
    assert AuthToken.objects.count() == 1
    assert con_token(cliente, cuenta_con_sesion).get('/auth/users/me/').status_code == 401


def test_usarla_la_vuelve_a_activar(cliente, cuenta_con_sesion):
    _sin_usar_desde_hace(cuenta_con_sesion, settings.SESION_ACTIVA + timedelta(minutes=1))
    # La app vuelve a avisar que sigue abierta: knox renueva el vencimiento.
    assert con_token(cliente, cuenta_con_sesion).get('/auth/users/me/').status_code == 200
    cliente.credentials()

    assert entrar(cliente).status_code == 409


def test_otra_cuenta_no_se_ve_afectada(cliente, cuenta_con_sesion):
    cliente.credentials()
    crear_cuenta(cliente, usuario='beto')

    assert entrar(cliente, usuario='beto').status_code == 200
