from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from knox.models import AuthToken
from knox.settings import CONSTANTS, knox_settings

from cuentas.views import sesion_en_otro_aparato

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
    assert respuesta.data['non_field_errors'] == [sesion_en_otro_aparato(5)]
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
    assert 'otro aparato' not in str(respuesta.data)


def test_cerrada_en_el_otro_aparato_deja_entrar(cliente, cuenta_con_sesion):
    con_token(cliente, cuenta_con_sesion).post('/auth/token/logout/')
    cliente.credentials()

    assert entrar(cliente).status_code == 200


def test_sin_usar_desde_hace_mas_de_un_rato_la_entrada_nueva_la_cierra(cliente, cuenta_con_sesion):
    _sin_usar_desde_hace(cuenta_con_sesion, settings.SESION_SIN_USO + timedelta(minutes=1))
    cliente.credentials()

    respuesta = entrar(cliente)

    assert respuesta.status_code == 200
    assert AuthToken.objects.count() == 1
    assert con_token(cliente, cuenta_con_sesion).get('/auth/users/me/').status_code == 401


def test_usarla_le_devuelve_los_cinco_minutos(cliente, cuenta_con_sesion):
    _sin_usar_desde_hace(cuenta_con_sesion, timedelta(minutes=3))
    # La app avisa que sigue abierta: knox renueva el vencimiento.
    assert con_token(cliente, cuenta_con_sesion).get('/auth/users/me/').status_code == 200
    cliente.credentials()

    respuesta = entrar(cliente)

    assert respuesta.status_code == 409
    assert respuesta.data['non_field_errors'] == [sesion_en_otro_aparato(5)]


def test_una_sesion_vencida_no_se_puede_reactivar_usandola(cliente, cuenta_con_sesion):
    _sin_usar_desde_hace(cuenta_con_sesion, settings.SESION_SIN_USO + timedelta(minutes=1))

    assert con_token(cliente, cuenta_con_sesion).get('/auth/users/me/').status_code == 401
    cliente.credentials()
    assert entrar(cliente).status_code == 200


def test_otra_cuenta_no_se_ve_afectada(cliente, cuenta_con_sesion):
    cliente.credentials()
    crear_cuenta(cliente, usuario='beto')

    assert entrar(cliente, usuario='beto').status_code == 200


def test_el_409_dice_cuantos_minutos_faltan(cliente, cuenta_con_sesion):
    # Sin usar hace 3 minutos: le faltan 2 para vencer.
    _sin_usar_desde_hace(cuenta_con_sesion, timedelta(minutes=3))
    cliente.credentials()

    respuesta = entrar(cliente)

    assert respuesta.status_code == 409
    assert respuesta.data['non_field_errors'] == [sesion_en_otro_aparato(2)]
    assert 'espera 2 minutos' in respuesta.data['non_field_errors'][0]


def test_un_minuto_se_dice_en_singular(cliente, cuenta_con_sesion):
    _sin_usar_desde_hace(cuenta_con_sesion, timedelta(minutes=4, seconds=30))
    cliente.credentials()

    mensaje = entrar(cliente).data['non_field_errors'][0]

    assert 'espera 1 minuto ' in mensaje


def test_la_sesion_dura_cinco_minutos_sin_uso(cliente, cuenta_con_sesion):
    assert knox_settings.TOKEN_TTL == settings.SESION_SIN_USO == timedelta(minutes=5)
    _sin_usar_desde_hace(cuenta_con_sesion, timedelta(minutes=5, seconds=1))

    assert con_token(cliente, cuenta_con_sesion).get('/auth/users/me/').status_code == 401
