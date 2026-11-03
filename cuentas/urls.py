"""Las rutas de la API, todas bajo `/auth/`.

Se declaran una por una, en vez de incluir todas las de djoser: así solo
existen las cinco que usa la app. No hay rutas por id, así que nadie puede
pedir ni borrar la cuenta de otro.
"""

from django.urls import path
from knox.views import LogoutView

from .views import Entrar, Usuarios

urlpatterns = [
    path('users/', Usuarios.as_view({'post': 'create'}), name='crear-cuenta'),
    path('users/me/', Usuarios.as_view({'get': 'me', 'delete': 'me'}), name='mi-cuenta'),
    path('token/login/', Entrar.as_view(), name='entrar'),
    path('token/logout/', LogoutView.as_view(), name='salir'),
]
