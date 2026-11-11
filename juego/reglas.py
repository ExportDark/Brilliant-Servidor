"""Las reglas de color del juego: qué números puede tener cada zona.

Son las mismas reglas que tiene la app en `lib/reglas/` (Dart), portadas a Python.
Los casos de `datos/casos_de_jugadas.json`, que genera la app con sus reglas, se
corren en `tests/test_paridad.py`: si una regla cambia en un lado y no en el otro,
ese test falla.
"""

# Qué zonas hay y cómo se llaman en los archivos compartidos con la app.
TIPOS = ('amarillo', 'verde', 'morado', 'azul', 'rojo', 'gris', 'naranja_bajo', 'naranja_alto')


def puede_agregar(tipo: str, numeros: list[int], numero: int) -> bool:
    """Si [numero] cabe en una zona de [tipo] que ya tiene anotados [numeros]."""
    if tipo in ('amarillo', 'rojo'):
        # Todos diferentes.
        return numero not in numeros
    if tipo == 'verde':
        # Cualquiera.
        return True
    if tipo == 'morado':
        # Como mucho dos números diferentes en toda la zona.
        return len({*numeros, numero}) <= 2
    if tipo in ('azul', 'gris'):
        # Todos iguales.
        return all(n == numero for n in numeros)
    if tipo == 'naranja_bajo':
        return 1 <= numero <= 3
    if tipo == 'naranja_alto':
        return 4 <= numero <= 6
    raise ValueError(f'Tipo de zona desconocido: {tipo!r}')
