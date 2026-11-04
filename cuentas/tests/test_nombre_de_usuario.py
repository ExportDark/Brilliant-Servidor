import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from cuentas.serializers import (
    USUARIO_CON_CARACTERES_RAROS,
    USUARIO_DE_OTRO_LARGO,
    USUARIO_REPETIDO,
)

from .conftest import crear_cuenta

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('usuario', ['ana', 'a' * 20, 'Ana_1.x-2', '007', 'luz.del-sol'])
def test_acepta_de_3_a_20_letras_sin_acento_numeros_punto_y_guiones(cliente, usuario):
    respuesta = crear_cuenta(cliente, usuario=usuario)

    assert respuesta.status_code == 201, respuesta.data
    assert respuesta.data['username'] == usuario


@pytest.mark.parametrize(
    ('usuario', 'mensaje'),
    [
        ('an', USUARIO_DE_OTRO_LARGO),
        ('a' * 21, USUARIO_DE_OTRO_LARGO),
        ('a' * 500, USUARIO_DE_OTRO_LARGO),
        ('ana pérez', USUARIO_CON_CARACTERES_RAROS),
        ('аna', USUARIO_CON_CARACTERES_RAROS),  # la primera "а" es cirílica
        ('ana@correo', USUARIO_CON_CARACTERES_RAROS),
        ('ana+1', USUARIO_CON_CARACTERES_RAROS),
        ('ñandu', USUARIO_CON_CARACTERES_RAROS),
        ('josé', USUARIO_CON_CARACTERES_RAROS),
        ('ana💎', USUARIO_CON_CARACTERES_RAROS),
        ('<script>', USUARIO_CON_CARACTERES_RAROS),
        ("' OR 1=1 --", USUARIO_CON_CARACTERES_RAROS),
        ('ana\tclara', USUARIO_CON_CARACTERES_RAROS),
        ('ana\nclara', USUARIO_CON_CARACTERES_RAROS),
    ],
)
def test_rechaza_otros_largos_y_caracteres_con_su_mensaje(cliente, usuario, mensaje):
    respuesta = crear_cuenta(cliente, usuario=usuario)

    assert respuesta.status_code == 400
    assert respuesta.data['username'] == [mensaje]
    assert not get_user_model().objects.exists()


@pytest.mark.parametrize('usuario', ['', '   ', 'ana\x00', None, ['ana'], {'nombre': 'ana'}])
def test_rechaza_vacios_nulos_y_lo_que_no_es_texto(cliente, usuario):
    respuesta = cliente.post(
        '/auth/users/',
        {'username': usuario, 'password': 'gema-brillante-73', 're_password': 'gema-brillante-73'},
        format='json',
    )

    assert respuesta.status_code == 400
    assert 'username' in respuesta.data
    assert not get_user_model().objects.exists()


def test_recorta_los_espacios_del_borde(cliente):
    respuesta = crear_cuenta(cliente, usuario='  ana  ')

    assert respuesta.status_code == 201
    assert get_user_model().objects.get().username == 'ana'


def test_no_distingue_mayusculas_y_guarda_el_nombre_como_se_escribio(cliente):
    assert crear_cuenta(cliente, usuario='Ana').status_code == 201

    for repetido in ('ana', 'ANA', 'aNa'):
        respuesta = crear_cuenta(cliente, usuario=repetido)
        assert respuesta.status_code == 400, repetido
        assert respuesta.data['username'] == [USUARIO_REPETIDO]

    assert list(get_user_model().objects.values_list('username', flat=True)) == ['Ana']


def test_la_base_no_deja_dos_nombres_que_solo_cambian_en_mayusculas():
    # Por si dos registros llegan a la vez y los dos pasan la revisión.
    get_user_model().objects.create_user('ana', password='gema-brillante-73')

    with pytest.raises(IntegrityError):
        get_user_model().objects.create_user('ANA', password='gema-brillante-73')
