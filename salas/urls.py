"""Las rutas de las salas, todas bajo `/salas/`."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.Crear.as_view(), name='crear-sala'),
    path('<str:codigo>/', views.DetalleDeSala.as_view(), name='sala'),
    path('<str:codigo>/unirse/', views.Unirse.as_view(), name='unirse'),
    path('<str:codigo>/mapa/', views.ElegirMapa.as_view(), name='mapa'),
    path('<str:codigo>/empezar/', views.Empezar.as_view(), name='empezar'),
    path('<str:codigo>/preparacion/', views.Preparacion.as_view(), name='preparacion'),
    path('<str:codigo>/jugada/', views.Jugada.as_view(), name='jugada'),
    path('<str:codigo>/rendirse/', views.Rendirse.as_view(), name='rendirse'),
]
