import pytest

from .conftest import con_token, crear_cuenta, entrar

pytestmark = pytest.mark.django_db


def test_con_usuario_y_contrasena_devuelve_un_token_que_vence(cliente):
    crear_cuenta(cliente)

    respuesta = entrar(cliente)

    assert respuesta.status_code == 200
    assert len(respuesta.data['token']) >= 64
    assert respuesta.data['expiry']


def test_cada_inicio_de_sesion_da_un_token_distinto(cliente):
    crear_cuenta(cliente)
    primero = entrar(cliente).data['token']
    con_token(cliente, primero).post('/auth/token/logout/')
    cliente.credentials()

    assert entrar(cliente).data['token'] != primero


def test_no_distingue_mayusculas(cliente):
    crear_cuenta(cliente, usuario='ana')

    respuesta = entrar(cliente, usuario='ANA')

    assert respuesta.status_code == 200
    assert con_token(cliente, respuesta.data['token']).get('/auth/users/me/').data['username'] == 'ana'


def test_usuario_o_contrasena_que_no_son_texto_no_entran(cliente):
    crear_cuenta(cliente)

    for datos in ({'username': ['ana'], 'password': 'x'}, {'username': 'ana', 'password': None}, {}):
        respuesta = cliente.post('/auth/token/login/', datos, format='json')
        assert respuesta.status_code == 400, datos
        assert 'token' not in respuesta.data


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
