"""Las salas del multijugador: el lobby, la preparación, las rondas, los puntos y las
desconexiones. Python puro, sin Django, para que se pueda probar entero.

El servidor manda: tira los dados, valida cada jugada con las reglas del juego
(`juego/`) y calcula los puntos. Nadie ve el tablero de otro: cada jugador recibe el
suyo, y de los demás solo lo que es público (quién ya jugó, sus puntos, qué zonas
llenó).

El tiempo lo mueve una sola función, `_actualizar`, que corre al inicio de cada pedido
y recibe la hora de un reloj que los tests pueden cambiar. No hay hilos ni
temporizadores: una sala "se entera" de que alguien se desconectó o de que se acabó el
tiempo de la ronda cuando alguien le pregunta.
"""

import random
import secrets
import threading
import time
from dataclasses import dataclass, field

from juego import puntuacion
from juego.tablero import Tablero, casilla_valida, mapas
from juego.validacion import (
    VALIDA,
    acepta_como_inicial,
    evaluar_jugada,
    hay_jugada,
    hay_jugada_posible,
    jugadas_legales,
)

MAXIMO_DE_JUGADORES = 6
MINIMO_PARA_EMPEZAR = 2
SEGUNDOS_PARA_DESCONECTAR = 10
SEGUNDOS_POR_RONDA = 60
SEGUNDOS_DE_PREPARACION = 60
SEGUNDOS_PARA_LIMPIAR = 600

# Sin los caracteres que se confunden al dictar un código: 0 y O, 1, I y L.
ALFABETO_DEL_CODIGO = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
LARGO_DEL_CODIGO = 6

# Estados de la sala.
ESPERANDO = 'esperando'
PREPARANDO = 'preparando'
JUGANDO = 'jugando'
TERMINADA = 'terminada'

# Estados de un jugador.
ACTIVO = 'activo'
SE_RINDIO = 'se_rindio'
DESCONECTADO = 'desconectado'

# Lo que hizo un jugador en la ronda.
PENDIENTE = 'pendiente'
COLOCO = 'coloco'
PASO = 'paso'

# Por qué terminó una partida.
TABLERO_LLENO = 'tablero_lleno'
SIN_JUGADAS = 'sin_jugadas'
ANFITRION_SE_FUE = 'anfitrion_se_fue'
# El anfitrión se fue del lobby, antes de empezar: no hubo partida, la sala se cerró.
SALA_CERRADA = 'sala_cerrada'
ULTIMO_JUGADOR = 'ultimo_jugador'
TODOS_SE_FUERON = 'todos_se_fueron'


class ErrorDeSala(Exception):
    """Un pedido que no se puede cumplir. [codigo] es estable (la app decide qué decir
    con él), [estado_http] es el código HTTP que le toca."""

    def __init__(self, codigo: str, mensaje: str, estado_http: int = 400, **detalles):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.estado_http = estado_http
        self.detalles = detalles


@dataclass
class Jugador:
    usuario: str
    ultimo_contacto: float
    estado: str = ACTIVO
    tablero: Tablero | None = None
    preparado: bool = False
    accion: str = PENDIENTE
    puntos: int = 0
    primeros: int = 0
    # zona -> (puesto, ronda en que la llenó)
    zonas: dict[int, tuple[int, int]] = field(default_factory=dict)


@dataclass
class Sala:
    codigo: str
    anfitrion: str
    nivel: int = 1
    estado: str = ESPERANDO
    jugadores: dict[str, Jugador] = field(default_factory=dict)
    ronda: int = 0
    dados: tuple[int, int] | None = None
    limite: float | None = None
    motivo: str | None = None
    ganadores: list[str] = field(default_factory=list)
    terminada_en: float | None = None
    # zona -> quiénes la llenaron, en orden: {'usuario', 'puesto', 'ronda'}
    puestos: dict[int, list[dict]] = field(default_factory=dict)
    version: int = 1

    def cambio(self) -> None:
        self.version += 1

    def activos(self) -> list[Jugador]:
        return [j for j in self.jugadores.values() if j.estado == ACTIVO]


class Salas:
    """Todas las salas, en memoria. Si el servidor se reinicia, las partidas terminan."""

    def __init__(self, reloj=time.monotonic, tirar_dado=None, azar: random.Random | None = None):
        self._reloj = reloj
        self._azar = azar or random.Random()
        self._tirar_dado = tirar_dado or (lambda: self._azar.randint(1, 6))
        self._salas: dict[str, Sala] = {}
        self._cerrojo = threading.RLock()

    # ------------------------------------------------------------------ lobby

    def crear(self, usuario: str) -> Sala:
        with self._cerrojo:
            ahora = self._reloj()
            self._limpiar(ahora)
            self._exigir_sin_sala(usuario, ahora)
            sala = Sala(codigo=self._codigo_nuevo(), anfitrion=usuario)
            sala.jugadores[usuario] = Jugador(usuario, ahora)
            self._salas[sala.codigo] = sala
            return sala

    def unirse(self, codigo: str, usuario: str) -> Sala:
        with self._cerrojo:
            ahora = self._reloj()
            sala = self._sala(codigo, ahora)
            if usuario in sala.jugadores and sala.jugadores[usuario].estado == ACTIVO:
                raise ErrorDeSala('ya_estas_en_la_sala', 'Ya estás en esta sala.', 409)
            if sala.estado != ESPERANDO:
                raise ErrorDeSala('ya_empezo', 'La partida ya empezó o terminó.', 409)
            self._exigir_sin_sala(usuario, ahora)
            if len(sala.jugadores) >= MAXIMO_DE_JUGADORES:
                raise ErrorDeSala('sala_llena', f'La sala ya tiene {MAXIMO_DE_JUGADORES} jugadores.', 409)
            sala.jugadores[usuario] = Jugador(usuario, ahora)
            sala.cambio()
            return sala

    def elegir_mapa(self, codigo: str, usuario: str, nivel) -> Sala:
        with self._cerrojo:
            ahora = self._reloj()
            sala, _ = self._miembro(codigo, usuario, ahora)
            self._exigir_anfitrion(sala, usuario)
            if sala.estado != ESPERANDO:
                raise ErrorDeSala('estado_incorrecto', 'El mapa solo se elige antes de empezar.', 409)
            if isinstance(nivel, bool) or not isinstance(nivel, int) or nivel not in mapas():
                raise ErrorDeSala('mapa_invalido', 'Ese mapa no existe.')
            if sala.nivel != nivel:
                sala.nivel = nivel
                sala.cambio()
            return sala

    def empezar(self, codigo: str, usuario: str) -> Sala:
        with self._cerrojo:
            ahora = self._reloj()
            sala, _ = self._miembro(codigo, usuario, ahora)
            self._exigir_anfitrion(sala, usuario)
            if sala.estado != ESPERANDO:
                raise ErrorDeSala('estado_incorrecto', 'La partida ya empezó.', 409)
            if len(sala.activos()) < MINIMO_PARA_EMPEZAR:
                raise ErrorDeSala(
                    'pocos_jugadores',
                    f'Hacen falta al menos {MINIMO_PARA_EMPEZAR} jugadores para empezar.',
                    409,
                )
            sala.estado = PREPARANDO
            sala.limite = ahora + SEGUNDOS_DE_PREPARACION
            for jugador in sala.jugadores.values():
                jugador.tablero = Tablero.vacio(sala.nivel)
            sala.cambio()
            return sala

    def rendirse(self, codigo: str, usuario: str) -> Sala:
        """Salirse de la sala. En el lobby, simplemente sale (si es el anfitrión, la sala
        se cierra); en la partida, queda fuera y los demás siguen."""
        with self._cerrojo:
            ahora = self._reloj()
            sala, jugador = self._miembro(codigo, usuario, ahora)
            if sala.estado == ESPERANDO:
                self._salir_del_lobby(sala, usuario, ahora)
            elif sala.estado in (PREPARANDO, JUGANDO) and jugador.estado == ACTIVO:
                jugador.estado = SE_RINDIO
                sala.cambio()
                self._actualizar(sala, ahora)
            return sala

    # ----------------------------------------------------------- preparación

    def preparar(self, codigo: str, usuario: str, valores) -> Sala:
        """Los números iniciales: del 1 al 6, uno en cada casilla inicial del mapa."""
        with self._cerrojo:
            ahora = self._reloj()
            sala, jugador = self._miembro(codigo, usuario, ahora)
            if sala.estado != PREPARANDO:
                raise ErrorDeSala('estado_incorrecto', 'Ahora no se están repartiendo números.', 409)
            self._exigir_activo(jugador)
            if jugador.preparado:
                raise ErrorDeSala('ya_preparaste', 'Ya repartiste tus números.', 409)

            iniciales = mapas()[sala.nivel].iniciales
            self._validar_reparto(jugador.tablero, iniciales, valores)
            for casilla in iniciales:
                jugador.tablero.poner(casilla, valores[casilla])
            jugador.preparado = True
            sala.cambio()
            self._actualizar(sala, ahora)
            return sala

    @staticmethod
    def _validar_reparto(tablero: Tablero, iniciales, valores) -> None:
        if not isinstance(valores, dict) or set(valores) != set(iniciales):
            raise ErrorDeSala(
                'preparacion_invalida',
                'Hay que dar un número para cada casilla inicial.',
                motivo='casillas',
            )
        numeros = list(valores.values())
        if any(isinstance(n, bool) or not isinstance(n, int) for n in numeros) or sorted(numeros) != [1, 2, 3, 4, 5, 6]:
            raise ErrorDeSala(
                'preparacion_invalida',
                'Tienen que ser los números del 1 al 6, sin repetir.',
                motivo='numeros',
            )
        for casilla, numero in valores.items():
            if not acepta_como_inicial(tablero, casilla, numero):
                raise ErrorDeSala(
                    'preparacion_invalida',
                    f'El {numero} no cabe en {casilla}.',
                    motivo='zona',
                )

    # -------------------------------------------------------------- la partida

    def jugar(self, codigo: str, usuario: str, ronda, dado_ancla, casilla) -> Sala:
        """Anota el otro dado en [casilla], pegada a una casilla con el número del dado
        ancla, [dado_ancla]."""
        with self._cerrojo:
            ahora = self._reloj()
            sala, jugador = self._miembro(codigo, usuario, ahora)
            self._exigir_ronda(sala, jugador, ronda)
            dados = sala.dados
            if isinstance(dado_ancla, bool) or dado_ancla not in dados:
                raise ErrorDeSala('dado_invalido', 'Ese número no salió en los dados.')
            if not casilla_valida(casilla):
                raise ErrorDeSala('casilla_invalida', 'Esa casilla no existe.')

            valor = dados[1] if dado_ancla == dados[0] else dados[0]
            resultado = evaluar_jugada(jugador.tablero, casilla, dado_ancla, valor)
            if resultado != VALIDA:
                raise ErrorDeSala(
                    'jugada_invalida', 'Ahí no se puede anotar.', motivo=resultado,
                )
            jugador.tablero.poner(casilla, valor)
            jugador.accion = COLOCO
            sala.cambio()
            self._actualizar(sala, ahora)
            return sala

    def pasar(self, codigo: str, usuario: str, ronda) -> Sala:
        """Pasar el turno. Solo se puede si con esta tirada no hay jugada, con ninguno
        de los dos dados como ancla."""
        with self._cerrojo:
            ahora = self._reloj()
            sala, jugador = self._miembro(codigo, usuario, ahora)
            self._exigir_ronda(sala, jugador, ronda)
            a, b = sala.dados
            if hay_jugada(jugador.tablero, a, b) or hay_jugada(jugador.tablero, b, a):
                raise ErrorDeSala('tienes_jugada', 'Con esta tirada sí tienes dónde anotar.', 409)
            jugador.accion = PASO
            sala.cambio()
            self._actualizar(sala, ahora)
            return sala

    def _exigir_ronda(self, sala: Sala, jugador: Jugador, ronda) -> None:
        if sala.estado != JUGANDO:
            raise ErrorDeSala('estado_incorrecto', 'La partida no está en juego.', 409)
        self._exigir_activo(jugador)
        if isinstance(ronda, bool) or ronda != sala.ronda:
            raise ErrorDeSala('ronda_incorrecta', 'Esa ronda ya pasó.', 409, ronda_actual=sala.ronda)
        if jugador.accion != PENDIENTE:
            raise ErrorDeSala('ya_jugaste', 'Ya jugaste esta ronda.', 409)

    # ------------------------------------------------------------------ estado

    def estado(self, codigo: str, usuario: str, version: int | None = None) -> dict | None:
        """Lo que ve [usuario] de la sala, o `None` si no cambió desde [version]. Preguntar
        cuenta como estar conectado."""
        with self._cerrojo:
            ahora = self._reloj()
            sala = self._sala(codigo, ahora, actualizar=False)
            jugador = sala.jugadores.get(usuario)
            if jugador is None:
                raise ErrorDeSala('no_eres_parte', 'No estás en esta sala.', 403)
            if jugador.estado == ACTIVO:
                jugador.ultimo_contacto = ahora
            self._actualizar(sala, ahora)
            if version is not None and version == sala.version:
                return None
            return self._vista(sala, jugador, ahora)

    def sala_de(self, usuario: str) -> str | None:
        """El código de la sala en la que está [usuario] ahora, si está en alguna."""
        with self._cerrojo:
            actual = self._sala_activa_de(usuario, self._reloj())
            return actual.codigo if actual else None

    # ---------------------------------------------------------------- el tiempo

    def _actualizar(self, sala: Sala, ahora: float) -> None:
        """Mueve la sala hasta donde llega con la hora [ahora]: desconectados, salidas,
        tiempos vencidos y rondas completas. Es lo único que mueve el tiempo."""
        for _ in range(1000):
            if not self._un_paso(sala, ahora):
                return

    def _un_paso(self, sala: Sala, ahora: float) -> bool:
        """Hace una cosa pendiente. Verdadero si hizo algo (y hay que volver a mirar)."""
        if sala.estado == TERMINADA:
            return False

        for jugador in sala.jugadores.values():
            if jugador.estado == ACTIVO and ahora - jugador.ultimo_contacto > SEGUNDOS_PARA_DESCONECTAR:
                if sala.estado == ESPERANDO:
                    self._salir_del_lobby(sala, jugador.usuario, ahora)
                else:
                    jugador.estado = DESCONECTADO
                    sala.cambio()
                return True

        if sala.estado == ESPERANDO:
            return False

        if self._aplicar_salidas(sala, ahora):
            return True

        if sala.estado == PREPARANDO:
            vencida = ahora >= sala.limite
            if vencida:
                for jugador in sala.activos():
                    if not jugador.preparado:
                        self._repartir_al_azar(sala, jugador)
            if vencida or all(j.preparado for j in sala.activos()):
                sala.estado = JUGANDO
                self._siguiente_ronda(sala, ahora)
                sala.cambio()
                return True
            return False

        # JUGANDO
        if ahora >= sala.limite:
            for jugador in sala.activos():
                if jugador.accion == PENDIENTE:
                    jugador.accion = PASO
            sala.cambio()
        if all(j.accion != PENDIENTE for j in sala.activos()):
            self._cerrar_ronda(sala, ahora)
            return True
        return False

    def _aplicar_salidas(self, sala: Sala, ahora: float) -> bool:
        """Las reglas de salida. Se va el anfitrión: ganan los demás. Queda uno solo: gana.
        No queda nadie: nadie gana."""
        activos = sala.activos()
        if not activos:
            self._terminar(sala, TODOS_SE_FUERON, [], ahora)
            return True
        if sala.jugadores[sala.anfitrion].estado != ACTIVO:
            self._terminar(sala, ANFITRION_SE_FUE, [j.usuario for j in activos], ahora)
            return True
        if len(activos) == 1:
            self._terminar(sala, ULTIMO_JUGADOR, [activos[0].usuario], ahora)
            return True
        return False

    def _terminar(self, sala: Sala, motivo: str, ganadores: list[str], ahora: float) -> None:
        sala.estado = TERMINADA
        sala.motivo = motivo
        sala.ganadores = ganadores
        sala.terminada_en = ahora
        sala.limite = None
        sala.cambio()

    def _salir_del_lobby(self, sala: Sala, usuario: str, ahora: float) -> None:
        if usuario == sala.anfitrion:
            # Sin anfitrión no hay quien empiece: la sala se cierra. No hubo partida, así
            # que no es "ganan los demás".
            self._terminar(sala, SALA_CERRADA, [], ahora)
            return
        sala.jugadores.pop(usuario, None)
        sala.cambio()

    # ------------------------------------------------------------------ rondas

    def _siguiente_ronda(self, sala: Sala, ahora: float) -> None:
        """Tira los dados de la ronda que sigue, o termina la partida si ya nadie puede
        jugar. Los que no tienen jugada con la tirada pasan solos; si pasan todos, se tira
        otra vez."""
        for _ in range(1000):
            activos = sala.activos()
            if all(j.tablero.lleno() or not hay_jugada_posible(j.tablero) for j in activos):
                motivo = TABLERO_LLENO if all(j.tablero.lleno() for j in activos) else SIN_JUGADAS
                self._terminar(sala, motivo, self._ganadores_por_puntos(sala), ahora)
                return

            sala.ronda += 1
            sala.dados = (self._tirar_dado(), self._tirar_dado())
            sala.limite = ahora + SEGUNDOS_POR_RONDA
            a, b = sala.dados
            for jugador in activos:
                sin_jugada = not (hay_jugada(jugador.tablero, a, b) or hay_jugada(jugador.tablero, b, a))
                jugador.accion = PASO if sin_jugada else PENDIENTE
            if any(j.accion == PENDIENTE for j in activos):
                return
        self._terminar(sala, SIN_JUGADAS, self._ganadores_por_puntos(sala), ahora)

    def _cerrar_ronda(self, sala: Sala, ahora: float) -> None:
        """Todos jugaron: se reparten los puestos de las zonas que se llenaron en esta
        ronda y empieza la siguiente."""
        self._repartir_puestos(sala)
        sala.cambio()
        self._siguiente_ronda(sala, ahora)

    def _repartir_puestos(self, sala: Sala) -> None:
        for zona in mapas()[sala.nivel].zonas:
            tomados = sala.puestos.setdefault(zona.id, [])
            ya = {p['usuario'] for p in tomados}
            nuevos = [
                j for j in sala.jugadores.values()
                if j.tablero is not None and j.usuario not in ya and j.tablero.zona_llena(zona)
            ]
            if not nuevos:
                continue
            # Todos los que la llenaron en esta ronda toman el mismo puesto.
            puesto = puntuacion.puesto_que_sigue(len(tomados))
            puntos = puntuacion.puntos_del_puesto(sala.nivel, zona.tipo, puesto)
            for jugador in nuevos:
                tomados.append({'usuario': jugador.usuario, 'puesto': puesto, 'ronda': sala.ronda})
                jugador.zonas[zona.id] = (puesto, sala.ronda)
                jugador.puntos += puntos
                if puesto == 1:
                    jugador.primeros += 1

    @staticmethod
    def _ganadores_por_puntos(sala: Sala) -> list[str]:
        """Quien más puntos suma, y si empatan, quien más primeros puestos tenga. Si
        siguen empatados, ganan todos los empatados. Solo ganan los que siguen en la
        partida."""
        activos = sala.activos()
        if not activos:
            return []
        mejor = max((j.puntos, j.primeros) for j in activos)
        return [j.usuario for j in activos if (j.puntos, j.primeros) == mejor]

    def _repartir_al_azar(self, sala: Sala, jugador: Jugador) -> None:
        iniciales = mapas()[sala.nivel].iniciales
        for _ in range(1000):
            numeros = [1, 2, 3, 4, 5, 6]
            self._azar.shuffle(numeros)
            if all(acepta_como_inicial(jugador.tablero, c, n) for c, n in zip(iniciales, numeros)):
                break
        for casilla, numero in zip(iniciales, numeros):
            jugador.tablero.poner(casilla, numero)
        jugador.preparado = True

    # ----------------------------------------------------------------- vistas

    def _vista(self, sala: Sala, jugador: Jugador, ahora: float) -> dict:
        """Lo que ve [jugador]. De sí mismo, su tablero y sus jugadas; de los demás, solo lo
        público. Nunca el tablero de otro."""
        mapa = mapas()[sala.nivel]
        vista = {
            'codigo': sala.codigo,
            'version': sala.version,
            'estado': sala.estado,
            'nivel': sala.nivel,
            'anfitrion': sala.anfitrion,
            'ronda': sala.ronda,
            'dados': list(sala.dados) if sala.dados and sala.estado == JUGANDO else None,
            'segundos_restantes': (
                max(0.0, round(sala.limite - ahora, 1)) if sala.limite is not None else None
            ),
            'yo': self._vista_de_mi(sala, jugador),
            'jugadores': [
                {
                    'usuario': j.usuario,
                    'estado': j.estado,
                    'anfitrion': j.usuario == sala.anfitrion,
                    'listo': (
                        j.preparado if sala.estado == PREPARANDO
                        else j.accion != PENDIENTE if sala.estado == JUGANDO else False
                    ),
                    'puntos': j.puntos,
                    'primeros': j.primeros,
                    'zonas': sorted(j.zonas),
                }
                for j in sala.jugadores.values()
            ],
            'zonas': [self._vista_de_zona(sala, zona) for zona in mapa.zonas],
            'resultado': None,
        }
        if sala.estado == TERMINADA:
            vista['resultado'] = self._resultado(sala)
        return vista

    def _vista_de_mi(self, sala: Sala, jugador: Jugador) -> dict:
        mi = {
            'usuario': jugador.usuario,
            'estado': jugador.estado,
            'preparado': jugador.preparado,
            'accion': jugador.accion,
            'tablero': dict(jugador.tablero.valores) if jugador.tablero else {},
            'iniciales': list(mapas()[sala.nivel].iniciales),
            'jugadas': [],
            'puede_pasar': False,
        }
        puede_jugar = (
            sala.estado == JUGANDO and jugador.estado == ACTIVO and jugador.accion == PENDIENTE
        )
        if puede_jugar:
            a, b = sala.dados
            for ancla, valor in {(a, b), (b, a)}:
                mi['jugadas'].append({
                    'ancla': ancla,
                    'valor': valor,
                    'casillas': jugadas_legales(jugador.tablero, ancla, valor),
                })
            mi['jugadas'].sort(key=lambda j: j['ancla'])
            mi['puede_pasar'] = not any(j['casillas'] for j in mi['jugadas'])
        return mi

    @staticmethod
    def _vista_de_zona(sala: Sala, zona) -> dict:
        tomados = sala.puestos.get(zona.id, [])
        siguiente = puntuacion.puesto_que_sigue(len(tomados))
        agotada = puntuacion.agotada(len(tomados))
        return {
            'id': zona.id,
            'tipo': zona.tipo,
            'color': puntuacion.color_de(zona.tipo),
            'casillas': list(zona.casillas),
            'puestos': [dict(p) for p in tomados],
            'agotada': agotada,
            'puntos_siguiente': 0 if agotada else puntuacion.puntos_del_puesto(sala.nivel, zona.tipo, siguiente),
        }

    @staticmethod
    def _resultado(sala: Sala) -> dict:
        ranking = sorted(
            sala.jugadores.values(),
            key=lambda j: (j.estado == ACTIVO, j.puntos, j.primeros),
            reverse=True,
        )
        return {
            'motivo': sala.motivo,
            'ganadores': list(sala.ganadores),
            'ranking': [
                {'usuario': j.usuario, 'estado': j.estado, 'puntos': j.puntos, 'primeros': j.primeros}
                for j in ranking
            ],
        }

    # ---------------------------------------------------------------- ayudantes

    def _codigo_nuevo(self) -> str:
        # Con `secrets` y no con el azar de los dados: un código no se puede adivinar
        # sabiendo los anteriores.
        while True:
            codigo = ''.join(secrets.choice(ALFABETO_DEL_CODIGO) for _ in range(LARGO_DEL_CODIGO))
            if codigo not in self._salas:
                return codigo

    def _sala(self, codigo, ahora: float, actualizar: bool = True) -> Sala:
        sala = self._salas.get(codigo.strip().upper()) if isinstance(codigo, str) else None
        if sala is None:
            raise ErrorDeSala('sala_no_existe', 'No hay ninguna sala con ese código.', 404)
        if actualizar:
            self._actualizar(sala, ahora)
        return sala

    def _miembro(self, codigo, usuario: str, ahora: float) -> tuple[Sala, Jugador]:
        # Hablarle a la sala cuenta como estar conectado, igual que preguntar (`estado`):
        # el contacto se anota antes de mirar quién se desconectó. Si no, quien vuelve de
        # un silencio con una jugada quedaba fuera por su propio pedido.
        sala = self._sala(codigo, ahora, actualizar=False)
        jugador = sala.jugadores.get(usuario)
        if jugador is None:
            raise ErrorDeSala('no_eres_parte', 'No estás en esta sala.', 403)
        if jugador.estado == ACTIVO:
            jugador.ultimo_contacto = ahora
        self._actualizar(sala, ahora)
        return sala, jugador

    @staticmethod
    def _exigir_anfitrion(sala: Sala, usuario: str) -> None:
        if sala.anfitrion != usuario:
            raise ErrorDeSala('no_eres_anfitrion', 'Solo el anfitrión puede hacer eso.', 403)

    @staticmethod
    def _exigir_activo(jugador: Jugador) -> None:
        if jugador.estado != ACTIVO:
            raise ErrorDeSala('no_activo', 'Ya no estás en la partida.', 409)

    def _sala_activa_de(self, usuario: str, ahora: float) -> Sala | None:
        for sala in list(self._salas.values()):
            jugador = sala.jugadores.get(usuario)
            if jugador is None:
                continue
            self._actualizar(sala, ahora)
            jugador = sala.jugadores.get(usuario)
            if jugador is not None and jugador.estado == ACTIVO and sala.estado != TERMINADA:
                return sala
        return None

    def _exigir_sin_sala(self, usuario: str, ahora: float) -> None:
        if self._sala_activa_de(usuario, ahora) is not None:
            raise ErrorDeSala(
                'ya_estas_en_una_sala',
                'Tu partida anterior sigue abierta. Si cerraste la app, se libera sola en unos '
                'segundos.',
                409,
            )

    def _limpiar(self, ahora: float) -> None:
        """Olvida las salas terminadas hace rato."""
        for codigo, sala in list(self._salas.items()):
            if sala.estado == TERMINADA and ahora - (sala.terminada_en or ahora) > SEGUNDOS_PARA_LIMPIAR:
                del self._salas[codigo]
