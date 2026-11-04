"""Un índice único sobre el nombre de usuario en minúsculas: "Ana" y "ana" no
pueden ser dos cuentas, aunque dos registros lleguen al mismo tiempo.

Los nombres solo tienen letras sin acento, así que `lower()` de SQLite basta.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE UNIQUE INDEX cuentas_usuario_sin_mayusculas ON auth_user (lower(username));',
            reverse_sql='DROP INDEX cuentas_usuario_sin_mayusculas;',
        ),
    ]
