from django.urls import include, path

urlpatterns = [
    path('auth/', include('cuentas.urls')),
]
