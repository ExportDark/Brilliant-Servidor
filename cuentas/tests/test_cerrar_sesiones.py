from io import StringIO

import pytest
from django.core.management import call_command
from knox.models import AuthToken

from .conftest import con_token, crear_cuenta, entrar

pytestmark = pytest.mark.django_db


def test_cierra_las_sesiones_de_todas_las_cuentas(cliente, cuenta_con_sesion):
    token_de_ana = cuenta_con_sesion
    cliente.credentials()
    crear_cuenta(cliente, usuario='beto')
    token_de_beto = entrar(cliente, usuario='beto').data['token']
    salida = StringIO()

    call_command('cerrar_sesiones', stdout=salida)

    assert AuthToken.objects.count() == 0
    assert con_token(cliente, token_de_ana).get('/auth/users/me/').status_code == 401
    assert con_token(cliente, token_de_beto).get('/auth/users/me/').status_code == 401
    assert '2' in salida.getvalue()


def test_despues_de_cerrarlas_se_puede_volver_a_entrar(cliente, cuenta_con_sesion):
    call_command('cerrar_sesiones', stdout=StringIO())
    cliente.credentials()

    assert entrar(cliente).status_code == 200


def test_sin_sesiones_no_hace_nada_y_lo_dice(cliente):
    salida = StringIO()

    call_command('cerrar_sesiones', stdout=salida)

    assert 'No había' in salida.getvalue()
