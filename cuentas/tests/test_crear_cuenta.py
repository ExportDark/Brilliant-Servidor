import pytest
from django.contrib.auth import get_user_model

from .conftest import crear_cuenta

pytestmark = pytest.mark.django_db


def test_crea_la_cuenta_y_no_devuelve_la_contrasena(cliente):
    respuesta = crear_cuenta(cliente, usuario='ana')

    assert respuesta.status_code == 201
    assert respuesta.data['username'] == 'ana'
    assert 'password' not in respuesta.data
    assert get_user_model().objects.filter(username='ana').exists()


def test_rechaza_un_usuario_repetido(cliente):
    crear_cuenta(cliente, usuario='ana')

    respuesta = crear_cuenta(cliente, usuario='ana')

    assert respuesta.status_code == 400
    assert 'username' in respuesta.data
    assert get_user_model().objects.filter(username='ana').count() == 1


@pytest.mark.parametrize(
    ('contrasena', 'por_que'),
    [
        ('corta1!', 'tiene menos de 8 caracteres'),
        ('password', 'es una contraseña común'),
        ('83920571', 'es solo números'),
        ('anaclara2', 'se parece al nombre de usuario'),
    ],
)
def test_rechaza_una_contrasena_debil(cliente, contrasena, por_que):
    respuesta = crear_cuenta(cliente, usuario='anaclara', contrasena=contrasena)

    assert respuesta.status_code == 400, por_que
    assert 'password' in respuesta.data, por_que
    assert not get_user_model().objects.filter(username='anaclara').exists()


def test_rechaza_contrasenas_que_no_coinciden(cliente):
    respuesta = crear_cuenta(cliente, repetida='otra-cosa-distinta-9')

    assert respuesta.status_code == 400
    assert not get_user_model().objects.exists()


def test_los_errores_vienen_en_espanol(cliente):
    respuesta = crear_cuenta(cliente, contrasena='corta1!')

    assert 'demasiado corta' in ' '.join(respuesta.data['password'])


def test_limita_cuantas_cuentas_se_crean_desde_una_misma_ip(cliente):
    respuestas = [crear_cuenta(cliente, usuario=f'jugador{n}') for n in range(11)]

    assert [r.status_code for r in respuestas[:10]] == [201] * 10
    assert respuestas[10].status_code == 429
