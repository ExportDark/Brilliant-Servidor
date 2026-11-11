"""Los puntos de las zonas: cuántos da cada una según el mapa, el color y el puesto en
que se llena.

Cada zona se paga por separado y tiene sus propios tres puestos: si alguien se lleva el
primero de una zona azul, la otra zona azul del mapa sigue pagando el primero al primero
que la llene. Del cuarto puesto en adelante no da puntos.

Cuando varios jugadores llenan la misma zona en la misma ronda, todos toman el mismo
puesto, y el siguiente puesto se salta: dos primeros, y el siguiente es el tercero.
"""

# Puntos del 1.º, 2.º y 3.º puesto, por mapa (nivel) y color.
PUNTOS = {
    1: {
        'azul': (7, 5, 3),
        'verde': (4, 3, 2),
        'rojo': (6, 4, 2),
        'morado': (6, 4, 2),
        'amarillo': (8, 6, 4),
    },
    2: {
        'amarillo': (6, 4, 2),
        'morado': (6, 4, 2),
        'rojo': (6, 4, 2),
        'azul': (7, 5, 3),
        'verde': (4, 3, 2),
        'gris': (3, 2, 1),
    },
    3: {
        'morado': (7, 5, 3),
        'rojo': (6, 4, 2),
        'azul': (7, 5, 3),
        'verde': (6, 5, 4),
        'gris': (8, 6, 4),
        'amarillo': (7, 5, 3),
    },
    4: {
        'morado': (7, 5, 3),
        'azul': (8, 6, 4),
        'rojo': (6, 4, 2),
        'naranja': (6, 4, 3),
        'amarillo': (8, 6, 4),
        'verde': (3, 2, 1),
    },
}

PUESTOS_QUE_PAGAN = 3


def color_de(tipo: str) -> str:
    """El color de un tipo de zona: las dos zonas naranjas pagan igual."""
    return 'naranja' if tipo.startswith('naranja') else tipo


def puntos_del_puesto(nivel: int, tipo: str, puesto: int) -> int:
    """Los puntos que da el [puesto] (1, 2, 3...) de una zona de [tipo] en el mapa
    [nivel]. Del cuarto en adelante, 0."""
    if puesto < 1:
        raise ValueError(f'Puesto inválido: {puesto}')
    tabla = PUNTOS[nivel].get(color_de(tipo))
    if tabla is None:
        raise ValueError(f'El mapa {nivel} no tiene zonas {tipo!r}')
    return tabla[puesto - 1] if puesto <= PUESTOS_QUE_PAGAN else 0


def puesto_que_sigue(ya_la_llenaron: int) -> int:
    """El puesto que toman los que la llenan ahora, si [ya_la_llenaron] personas la
    habían llenado antes. Cuenta personas, no puestos: así dos primeros dejan al
    siguiente en el tercero."""
    return ya_la_llenaron + 1


def agotada(ya_la_llenaron: int) -> bool:
    """Si ya no da puntos a nadie: los tres puestos que pagan están tomados."""
    return ya_la_llenaron >= PUESTOS_QUE_PAGAN
