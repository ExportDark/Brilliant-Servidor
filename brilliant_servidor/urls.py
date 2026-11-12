from django.urls import include, path

from .views import QuienEres

urlpatterns = [
    path('auth/', include('cuentas.urls')),
    path('salas/', include('salas.urls')),
    path('servidor/', QuienEres.as_view()),
]
