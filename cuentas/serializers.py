"""Las reglas de las cuentas: cómo puede ser el nombre de usuario y cómo se
recibe la contraseña. Los serializers de djoser y de DRF hacen casi todo; aquí
se ajusta lo que les falta.
"""

import re

from django.contrib.auth import get_user_model
from djoser.serializers import UserCreatePasswordRetypeSerializer, UserDeleteSerializer
from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer

LARGO_MINIMO_USUARIO = 3
LARGO_MAXIMO_USUARIO = 20

# Más larga que cualquier contraseña de verdad. Sin un máximo, alguien podría
# mandar una gigante para que el servidor se cansara calculando su hash.
LARGO_MAXIMO_CONTRASENA = 128

# Solo letras sin acento, números, punto, guion y guion bajo: así no hay
# letras de otros alfabetos que se parezcan ("аna", en cirílico, no es "ana").
_CARACTERES_DEL_USUARIO = re.compile(r'[A-Za-z0-9._-]+')

USUARIO_DE_OTRO_LARGO = (
    f'El nombre de usuario debe tener entre {LARGO_MINIMO_USUARIO} y '
    f'{LARGO_MAXIMO_USUARIO} caracteres.'
)
USUARIO_CON_CARACTERES_RAROS = (
    'Solo puede tener letras sin acento, números, punto, guion y guion bajo.'
)
USUARIO_REPETIDO = 'Ya existe un usuario con este nombre.'


def _campo_de_contrasena(**opciones):
    """Una contraseña se recibe tal cual. DRF recorta los espacios del borde
    de cualquier texto, pero en una contraseña también son parte de ella: si
    se recortaran al crear la cuenta y no al entrar, no se podría entrar."""
    return serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False,
        max_length=LARGO_MAXIMO_CONTRASENA,
        **opciones,
    )


class CrearCuenta(UserCreatePasswordRetypeSerializer):
    """Crear la cuenta, con las reglas del nombre de usuario de Brilliant."""

    # Se declara aparte para que solo valgan las reglas de abajo, con sus
    # mensajes, y no las de Django (cualquier alfabeto, hasta 150, @ y +).
    username = serializers.CharField()
    password = _campo_de_contrasena(write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['re_password'] = _campo_de_contrasena()

    def validate_username(self, usuario):
        if not LARGO_MINIMO_USUARIO <= len(usuario) <= LARGO_MAXIMO_USUARIO:
            raise serializers.ValidationError(USUARIO_DE_OTRO_LARGO)
        if not _CARACTERES_DEL_USUARIO.fullmatch(usuario):
            raise serializers.ValidationError(USUARIO_CON_CARACTERES_RAROS)
        # "Ana" y "ana" son la misma cuenta. Además, la base tiene un índice
        # único sobre el nombre en minúsculas, por si dos llegan a la vez.
        if get_user_model().objects.filter(username__iexact=usuario).exists():
            raise serializers.ValidationError(USUARIO_REPETIDO)
        return usuario


class BorrarCuenta(UserDeleteSerializer):
    """Borrar la cuenta, con la contraseña actual tal cual se escribió."""

    current_password = _campo_de_contrasena()


class DatosParaEntrar(AuthTokenSerializer):
    """Usuario y contraseña para iniciar sesión, con la contraseña tal cual y
    un largo máximo para los dos."""

    username = serializers.CharField(write_only=True, max_length=150)
    password = _campo_de_contrasena(write_only=True)
