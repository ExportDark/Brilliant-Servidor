"""Desconexiones y salidas: lo que más puede romper una partida en línea.

Las reglas: quien deja de preguntar 10 segundos queda fuera (desconectado); quien se
rinde, también. Con 2 jugadores, si uno sale, gana el otro. Si se va el anfitrión,
ganan los demás. Con 3 o más, si se va otro, la partida sigue; si queda uno solo, gana.
"""

import pytest

from salas.dominio import (
    ACTIVO,
    ANFITRION_SE_FUE,
    DESCONECTADO,
    ESPERANDO,
    JUGANDO,
    PREPARANDO,
    SE_RINDIO,
    SEGUNDOS_PARA_DESCONECTAR,
    TERMINADA,
    TODOS_SE_FUERON,
    ULTIMO_JUGADOR,
    ErrorDeSala,
)

from .ayudantes import (
    REPARTO,
    armar_sala,
    empezar_partida,
    empezar_preparacion,
    latir,
    pasar_tiempo,
)


def _error(llamada) -> ErrorDeSala:
    with pytest.raises(ErrorDeSala) as capturado:
        llamada()
    return capturado.value


def _estado_de(salas, codigo, quien, usuario):
    return next(j for j in salas.estado(codigo, quien)['jugadores'] if j['usuario'] == usuario)['estado']


# ------------------------------------------------------------ el límite de 10 s


def test_con_9_segundos_sin_preguntar_todavia_esta_conectado(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    reloj.avanzar(SEGUNDOS_PARA_DESCONECTAR - 1)

    assert _estado_de(salas, codigo, 'ana', 'beto') == ACTIVO
    assert salas._salas[codigo].estado == JUGANDO


def test_con_mas_de_10_segundos_sin_preguntar_queda_fuera(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    pasar_tiempo(salas, reloj, codigo, ['ana'], SEGUNDOS_PARA_DESCONECTAR + 1)

    assert salas._salas[codigo].jugadores['beto'].estado == DESCONECTADO


def test_un_corte_breve_no_cuenta_si_vuelve_a_preguntar_a_tiempo(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    reloj.avanzar(9)
    salas.estado(codigo, 'beto')
    reloj.avanzar(9)
    salas.estado(codigo, 'ana')
    salas.estado(codigo, 'beto')

    assert salas._salas[codigo].estado == JUGANDO
    assert salas._salas[codigo].jugadores['beto'].estado == ACTIVO


# ------------------------------------------------------------- con 2 jugadores


def test_con_dos_jugadores_si_uno_se_desconecta_gana_el_otro(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    pasar_tiempo(salas, reloj, codigo, ['ana'], SEGUNDOS_PARA_DESCONECTAR + 1)

    vista = salas.estado(codigo, 'ana')
    assert vista['estado'] == TERMINADA
    assert vista['resultado']['motivo'] == ULTIMO_JUGADOR
    assert vista['resultado']['ganadores'] == ['ana']


def test_con_dos_jugadores_si_el_anfitrion_se_desconecta_gana_el_otro(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    pasar_tiempo(salas, reloj, codigo, ['beto'], SEGUNDOS_PARA_DESCONECTAR + 1)

    resultado = salas.estado(codigo, 'beto')['resultado']
    assert resultado['ganadores'] == ['beto']
    assert resultado['motivo'] == ANFITRION_SE_FUE


def test_con_dos_jugadores_si_uno_se_rinde_gana_el_otro(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    salas.rendirse(codigo, 'beto')

    resultado = salas.estado(codigo, 'ana')['resultado']
    assert resultado['ganadores'] == ['ana']
    assert resultado['motivo'] == ULTIMO_JUGADOR
    assert [r['usuario'] for r in resultado['ranking']] == ['ana', 'beto']
    assert resultado['ranking'][1]['estado'] == SE_RINDIO


# ---------------------------------------------------------------- el anfitrión


def test_si_se_va_el_anfitrion_ganan_todos_los_demas(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla', 'dani'])

    pasar_tiempo(salas, reloj, codigo, ['beto', 'carla', 'dani'], SEGUNDOS_PARA_DESCONECTAR + 1)

    resultado = salas.estado(codigo, 'beto')['resultado']
    assert resultado['motivo'] == ANFITRION_SE_FUE
    assert sorted(resultado['ganadores']) == ['beto', 'carla', 'dani']


def test_si_el_anfitrion_se_rinde_a_media_partida_ganan_los_demas(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])

    salas.rendirse(codigo, 'ana')

    resultado = salas.estado(codigo, 'beto')['resultado']
    assert resultado['motivo'] == ANFITRION_SE_FUE
    assert sorted(resultado['ganadores']) == ['beto', 'carla']


def test_si_el_anfitrion_se_va_en_la_preparacion_ganan_los_demas(salas, dados):
    codigo = empezar_preparacion(salas, ['ana', 'beto', 'carla'])

    salas.rendirse(codigo, 'ana')

    sala = salas._salas[codigo]
    assert sala.estado == TERMINADA
    assert sorted(sala.ganadores) == ['beto', 'carla']


def test_si_el_anfitrion_se_va_a_media_ronda_la_partida_termina_en_ese_momento(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])
    salas.jugar(codigo, 'beto', 1, 1, 'D1')  # a media ronda: falta ana y carla

    salas.rendirse(codigo, 'ana')

    assert salas._salas[codigo].estado == TERMINADA
    assert _error(lambda: salas.jugar(codigo, 'carla', 1, 1, 'D1')).codigo == 'estado_incorrecto'


# ------------------------------------------------------- con 3 o más jugadores


def test_con_tres_si_se_va_uno_la_partida_sigue(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])

    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_PARA_DESCONECTAR + 1)

    vista = salas.estado(codigo, 'ana')
    assert vista['estado'] == JUGANDO
    assert _estado_de(salas, codigo, 'ana', 'carla') == DESCONECTADO


def test_la_ronda_ya_no_espera_a_quien_se_fue(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])
    dados.poner(2, 3)
    salas.jugar(codigo, 'ana', 1, 1, 'D1')
    salas.jugar(codigo, 'beto', 1, 1, 'D1')
    assert salas.estado(codigo, 'ana')['ronda'] == 1  # falta carla

    salas.rendirse(codigo, 'carla')

    assert salas.estado(codigo, 'ana')['ronda'] == 2  # ya no se la espera


def test_si_van_quedando_menos_gana_el_ultimo(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla', 'dani'])

    salas.rendirse(codigo, 'dani')
    salas.rendirse(codigo, 'carla')
    assert salas._salas[codigo].estado == JUGANDO  # quedan ana y beto

    salas.rendirse(codigo, 'beto')

    resultado = salas.estado(codigo, 'ana')['resultado']
    assert (resultado['motivo'], resultado['ganadores']) == (ULTIMO_JUGADOR, ['ana'])


def test_quien_se_fue_puede_seguir_preguntando_y_ve_que_quedo_fuera(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])
    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_PARA_DESCONECTAR + 1)

    vista = salas.estado(codigo, 'carla')  # vuelve la conexión de carla

    assert vista['yo']['estado'] == DESCONECTADO
    assert vista['yo']['jugadas'] == []
    assert vista['estado'] == JUGANDO  # la partida siguió sin ella
    # Preguntar no la trae de vuelta.
    reloj.avanzar(1)
    assert salas.estado(codigo, 'carla')['yo']['estado'] == DESCONECTADO


def test_quien_se_fue_no_puede_jugar_ni_pasar_ni_repartir(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])
    salas.rendirse(codigo, 'carla')

    assert _error(lambda: salas.jugar(codigo, 'carla', 1, 1, 'D1')).codigo == 'no_activo'
    assert _error(lambda: salas.pasar(codigo, 'carla', 1)).codigo == 'no_activo'


def test_quien_se_rinde_dos_veces_no_rompe_nada(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])
    salas.rendirse(codigo, 'carla')

    salas.rendirse(codigo, 'carla')

    assert salas._salas[codigo].jugadores['carla'].estado == SE_RINDIO
    assert salas._salas[codigo].estado == JUGANDO


def test_rendirse_cuando_la_partida_ya_termino_no_cambia_el_resultado(salas, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    salas.rendirse(codigo, 'beto')
    antes = salas.estado(codigo, 'ana')['resultado']

    salas.rendirse(codigo, 'ana')

    assert salas.estado(codigo, 'ana')['resultado'] == antes


# -------------------------------------------------- todos se van a la vez


def test_si_los_dos_dejan_de_preguntar_gana_quien_vuelve_primero(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])

    reloj.avanzar(SEGUNDOS_PARA_DESCONECTAR + 1)
    # Los dos pasaron el límite. Ana vuelve a preguntar primero: preguntar cuenta como
    # estar conectado, así que la que vuelve primero sigue en la partida.
    vista = salas.estado(codigo, 'ana')

    assert vista['estado'] == TERMINADA
    assert vista['resultado']['ganadores'] == ['ana']
    assert vista['resultado']['motivo'] == ULTIMO_JUGADOR
    assert salas.estado(codigo, 'beto')['yo']['estado'] == DESCONECTADO


def test_si_se_desconectan_todos_nadie_gana(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])

    reloj.avanzar(SEGUNDOS_PARA_DESCONECTAR + 5)
    sala = salas._salas[codigo]
    salas._actualizar(sala, reloj())

    assert sala.estado == TERMINADA
    assert sala.motivo == TODOS_SE_FUERON
    assert sala.ganadores == []


def test_despues_de_que_todos_se_fueron_pueden_crear_otra_sala(salas, reloj, dados):
    codigo = empezar_partida(salas, dados, ['ana', 'beto'])
    reloj.avanzar(SEGUNDOS_PARA_DESCONECTAR + 5)

    nueva = salas.crear('ana').codigo

    assert nueva != codigo
    assert salas.sala_de('ana') == nueva


# --------------------------------------------------- en el lobby y la preparación


def test_en_el_lobby_quien_deja_de_preguntar_sale_de_la_sala(salas, reloj):
    codigo = armar_sala(salas, ['ana', 'beto', 'carla'])

    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_PARA_DESCONECTAR + 1)

    assert list(salas._salas[codigo].jugadores) == ['ana', 'beto']
    assert salas._salas[codigo].estado == ESPERANDO
    assert _error(lambda: salas.estado(codigo, 'carla')).codigo == 'no_eres_parte'


def test_en_el_lobby_si_el_anfitrion_deja_de_preguntar_la_sala_se_cierra(salas, reloj):
    codigo = armar_sala(salas, ['ana', 'beto'])

    pasar_tiempo(salas, reloj, codigo, ['beto'], SEGUNDOS_PARA_DESCONECTAR + 1)

    sala = salas._salas[codigo]
    assert sala.estado == TERMINADA
    assert sala.motivo == ANFITRION_SE_FUE
    assert salas.sala_de('beto') is None


def test_si_se_desconecta_quien_no_habia_repartido_la_partida_empieza_con_los_demas(
    salas, reloj, dados
):
    codigo = empezar_preparacion(salas, ['ana', 'beto', 'carla'])
    dados.poner(1, 3)
    salas.preparar(codigo, 'ana', REPARTO)
    salas.preparar(codigo, 'beto', REPARTO)
    assert salas._salas[codigo].estado == PREPARANDO  # falta carla

    pasar_tiempo(salas, reloj, codigo, ['ana', 'beto'], SEGUNDOS_PARA_DESCONECTAR + 1)

    sala = salas._salas[codigo]
    assert sala.estado == JUGANDO
    assert sala.jugadores['carla'].estado == DESCONECTADO


def test_en_la_preparacion_si_queda_uno_solo_gana(salas, dados):
    codigo = empezar_preparacion(salas, ['ana', 'beto'])

    salas.rendirse(codigo, 'beto')

    assert salas._salas[codigo].ganadores == ['ana']


def test_un_jugador_que_estaba_en_la_partida_y_se_fue_puede_entrar_a_otra_sala(
    salas, dados
):
    codigo = empezar_partida(salas, dados, ['ana', 'beto', 'carla'])
    salas.rendirse(codigo, 'carla')

    otra = salas.crear('carla').codigo

    assert salas.sala_de('carla') == otra
    assert salas._salas[codigo].estado == JUGANDO  # la partida de los otros sigue
