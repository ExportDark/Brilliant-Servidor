import pytest

from .conftest import crear_cuenta, entrar

pytestmark = pytest.mark.django_db


def test_con_usuario_y_contrasena_devuelve_un_token_que_vence(cliente):
    crear_cuenta(cliente)

    respuesta = entrar(cliente)

    assert respuesta.status_code == 200
    assert len(respuesta.data['token']) >= 64
    assert respuesta.data['expiry']


def test_cada_inicio_de_sesion_da_un_token_distinto(cliente):
    crear_cuenta(cliente)

    assert entrar(cliente).data['token'] != entrar(cliente).data['token']


def test_contrasena_mala_y_usuario_inexistente_dan_el_mismo_error(cliente):
    crear_cuenta(cliente)

    contrasena_mala = entrar(cliente, contrasena='no-es-la-buena-1')
    usuario_inexistente = entrar(cliente, usuario='nadie')

    # El mismo mensaje en los dos casos: así no se puede averiguar qué
    # usuarios existen probando contraseñas.
    assert contrasena_mala.status_code == 400
    assert usuario_inexistente.status_code == 400
    assert contrasena_mala.data == usuario_inexistente.data
    assert 'token' not in contrasena_mala.data


def test_limita_los_intentos_por_minuto(cliente):
    crear_cuenta(cliente)

    intentos = [entrar(cliente, contrasena=f'adivinando-{n}') for n in range(6)]

    assert [r.status_code for r in intentos[:5]] == [400] * 5
    assert intentos[5].status_code == 429
