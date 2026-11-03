import pytest
from django.contrib.auth import get_user_model

from .conftest import CONTRASENA, con_token, crear_cuenta

pytestmark = pytest.mark.django_db


def test_no_se_puede_listar_ni_pedir_la_cuenta_de_otro(cliente, cuenta_con_sesion):
    crear_cuenta(cliente, usuario='beto')
    beto = get_user_model().objects.get(username='beto')
    con_token(cliente, cuenta_con_sesion)

    assert cliente.get('/auth/users/').status_code == 405
    assert cliente.get(f'/auth/users/{beto.pk}/').status_code == 404


def test_no_se_puede_borrar_la_cuenta_de_otro(cliente, cuenta_con_sesion):
    crear_cuenta(cliente, usuario='beto')
    beto = get_user_model().objects.get(username='beto')

    respuesta = con_token(cliente, cuenta_con_sesion).delete(
        f'/auth/users/{beto.pk}/', {'current_password': CONTRASENA}, format='json'
    )

    assert respuesta.status_code == 404
    assert get_user_model().objects.filter(username='beto').exists()


def test_borrar_la_propia_cuenta_no_toca_las_demas(cliente, cuenta_con_sesion):
    crear_cuenta(cliente, usuario='beto')

    con_token(cliente, cuenta_con_sesion).delete(
        '/auth/users/me/', {'current_password': CONTRASENA}, format='json'
    )

    assert list(get_user_model().objects.values_list('username', flat=True)) == ['beto']
