"""Los mensajes que la app muestra tal cual: cortos, de tú, en español y que dicen lo que
pasó. Antes salían los de DRF, Django y djoser ("No puede iniciar sesión con las
credenciales proporcionadas.", "La contraseña es demasiado similar a la de nombre de
usuario.", "Asegúrese de que...")."""

import pytest

from cuentas.views import sesion_en_otro_aparato

from .conftest import CONTRASENA, con_token, crear_cuenta, entrar

pytestmark = pytest.mark.django_db


def test_usuario_o_contrasena_incorrectos(cliente):
    crear_cuenta(cliente)
    cliente.credentials()

    respuesta = entrar(cliente, contrasena='no-es-la-contrasena')

    assert respuesta.status_code == 400
    assert respuesta.data['non_field_errors'] == ['Usuario o contraseña incorrectos.']


def test_la_sesion_en_otro_aparato_es_corta():
    assert sesion_en_otro_aparato(5) == (
        'Tu cuenta está abierta en otro aparato. Ciérrala allá o espera 5 min.'
    )


def test_el_nombre_ya_esta_en_uso(cliente):
    crear_cuenta(cliente)

    respuesta = crear_cuenta(cliente, usuario='ANA')

    assert respuesta.data['username'] == ['Ese nombre ya está en uso']


@pytest.mark.parametrize(
    ('usuario', 'contrasena', 'mensajes'),
    [
        ('beto', '12345678', ['Es demasiado común', 'No puede ser solo números']),
        ('carlota99', 'carlota99', ['Se parece demasiado a tu usuario']),
        ('dario', 'corta1', ['Al menos 8 caracteres']),
    ],
)
def test_las_reglas_de_la_contrasena(cliente, usuario, contrasena, mensajes):
    respuesta = crear_cuenta(cliente, usuario=usuario, contrasena=contrasena)

    assert respuesta.status_code == 400
    assert respuesta.data['password'] == mensajes


def test_la_contrasena_incorrecta_al_borrar(cliente):
    crear_cuenta(cliente)
    token = entrar(cliente).data['token']

    respuesta = con_token(cliente, token).delete(
        '/auth/users/me/', {'current_password': 'no-es-la-contrasena'}, format='json'
    )

    assert respuesta.status_code == 400
    assert respuesta.data['current_password'] == ['Contraseña incorrecta.']


def test_un_usuario_demasiado_largo_al_entrar(cliente):
    respuesta = entrar(cliente, usuario='a' * 151, contrasena=CONTRASENA)

    assert respuesta.status_code == 400
    assert respuesta.data['username'] == ['Máximo 150 caracteres']
