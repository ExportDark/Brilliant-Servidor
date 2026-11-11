"""El registro de salas de este servidor: uno solo, en memoria.

Si el servidor se reinicia, las salas y las partidas en curso se pierden (igual que las
sesiones, que `iniciar.bat` cierra al arrancar). Los tests cambian `registro` por uno con
reloj y dados falsos.
"""

from .dominio import Salas

registro = Salas()
