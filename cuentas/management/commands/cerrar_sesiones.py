"""Cierra las sesiones de todas las cuentas: borra todos los tokens.

`iniciar.bat` lo corre cada vez que se arranca el servidor a mano. Las sesiones
están en la base de datos y sobreviven a un reinicio; sin esto, una sesión que
quedó abierta (el cierre de sesión no llegó) dejaría a su cuenta sin poder
entrar mientras no venza. Cada celular lo nota en su próximo aviso al servidor
y vuelve a "Iniciar sesión".
"""

from django.core.management.base import BaseCommand
from knox.models import AuthToken


class Command(BaseCommand):
    help = 'Cierra las sesiones de todas las cuentas.'

    def handle(self, *args, **opciones):
        cerradas, _ = AuthToken.objects.all().delete()
        if cerradas:
            self.stdout.write(f'Se cerraron {cerradas} sesiones abiertas.')
        else:
            self.stdout.write('No había sesiones abiertas.')
