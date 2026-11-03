import pytest
from django.contrib.auth import get_user_model
from knox.models import AuthToken

from .conftest import CONTRASENA

pytestmark = pytest.mark.django_db


def test_la_contrasena_se_guarda_con_argon2_y_nunca_en_texto(cliente, cuenta_con_sesion):
    guardada = get_user_model().objects.get(username='ana').password

    assert guardada.startswith('argon2$argon2id$')
    assert CONTRASENA not in guardada


def test_el_token_no_se_guarda_en_la_base_solo_su_hash(cliente, cuenta_con_sesion):
    (guardado,) = AuthToken.objects.all()

    # knox guarda el hash SHA-512 del token y un prefijo corto para
    # buscarlo, pero nunca el token completo.
    assert guardado.digest != cuenta_con_sesion
    assert cuenta_con_sesion not in guardado.digest
    assert len(guardado.token_key) < len(cuenta_con_sesion)
