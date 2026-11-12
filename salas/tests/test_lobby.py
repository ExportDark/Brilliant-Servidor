import threading

import pytest

from salas.dominio import (
    ALFABETO_DEL_CODIGO,
    SALA_CERRADA,
    ESPERANDO,
    LARGO_DEL_CODIGO,
    MAXIMO_DE_JUGADORES,
    PREPARANDO,
    TERMINADA,
    ErrorDeSala,
    Salas,
)

from .ayudantes import armar_sala


def _error(llamada) -> ErrorDeSala:
    with pytest.raises(ErrorDeSala) as capturado:
        llamada()
    return capturado.value


def test_crear_una_sala_da_un_codigo_de_6_caracteres_sin_los_que_se_confunden(salas):
    codigos = {salas.crear(f'jugador{n}').codigo for n in range(200)}

    assert len(codigos) == 200  # no se repiten
    for codigo in codigos:
        assert len(codigo) == LARGO_DEL_CODIGO
        assert set(codigo) <= set(ALFABETO_DEL_CODIGO)
        assert not set(codigo) & set('0O1IL')


def test_quien_crea_la_sala_es_el_anfitrion_y_esta_esperando(salas):
    sala = salas.crear('ana')

    assert sala.anfitrion == 'ana'
    assert sala.estado == ESPERANDO
    assert list(sala.jugadores) == ['ana']


def test_unirse_con_el_codigo_en_minusculas_tambien_funciona(salas):
    codigo = salas.crear('ana').codigo

    sala = salas.unirse(codigo.lower(), 'beto')

    assert list(sala.jugadores) == ['ana', 'beto']


def test_unirse_a_un_codigo_que_no_existe_da_404(salas):
    error = _error(lambda: salas.unirse('ZZZZZZ', 'beto'))

    assert (error.codigo, error.estado_http) == ('sala_no_existe', 404)


@pytest.mark.parametrize('codigo', ['', '   ', None, 123, 'K7M4Q', 'K7M4QXX', [], {}, ['A']])
def test_un_codigo_malformado_es_sala_inexistente_no_un_error_raro(salas, codigo):
    assert _error(lambda: salas.unirse(codigo, 'beto')).codigo == 'sala_no_existe'


def test_la_sala_admite_6_jugadores_y_el_septimo_no_entra(salas):
    codigo = salas.crear('j1').codigo
    for n in range(2, MAXIMO_DE_JUGADORES + 1):
        salas.unirse(codigo, f'j{n}')

    error = _error(lambda: salas.unirse(codigo, 'j7'))

    assert (error.codigo, error.estado_http) == ('sala_llena', 409)
    assert len(salas._salas[codigo].jugadores) == 6


def test_dos_unirse_a_la_vez_con_un_solo_lugar_dejan_pasar_a_uno(salas):
    codigo = salas.crear('j1').codigo
    for n in range(2, MAXIMO_DE_JUGADORES):
        salas.unirse(codigo, f'j{n}')  # quedan 5; falta un lugar

    resultados: list[str] = []

    def entrar(usuario):
        try:
            salas.unirse(codigo, usuario)
            resultados.append('entro')
        except ErrorDeSala as error:
            resultados.append(error.codigo)

    hilos = [threading.Thread(target=entrar, args=(f'extra{n}',)) for n in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert resultados.count('entro') == 1
    assert resultados.count('sala_llena') == 7
    assert len(salas._salas[codigo].jugadores) == 6


def test_no_se_puede_unir_dos_veces_a_la_misma_sala(salas):
    codigo = salas.crear('ana').codigo
    salas.unirse(codigo, 'beto')

    assert _error(lambda: salas.unirse(codigo, 'beto')).codigo == 'ya_estas_en_la_sala'
    assert _error(lambda: salas.unirse(codigo, 'ana')).codigo == 'ya_estas_en_la_sala'


def test_no_se_puede_estar_en_dos_salas_a_la_vez(salas):
    una = salas.crear('ana').codigo
    otra = salas.crear('carla').codigo

    assert _error(lambda: salas.unirse(otra, 'ana')).codigo == 'ya_estas_en_una_sala'
    assert _error(lambda: salas.crear('ana')).codigo == 'ya_estas_en_una_sala'
    assert salas.sala_de('ana') == una


def test_despues_de_salirse_se_puede_entrar_a_otra_sala(salas):
    una = salas.crear('ana').codigo
    salas.unirse(una, 'beto')
    salas.rendirse(una, 'beto')
    otra = salas.crear('carla').codigo

    salas.unirse(otra, 'beto')

    assert salas.sala_de('beto') == otra


def test_no_se_puede_unir_a_una_partida_que_ya_empezo(salas):
    codigo = armar_sala(salas, ['ana', 'beto'])
    salas.empezar(codigo, 'ana')

    assert _error(lambda: salas.unirse(codigo, 'carla')).codigo == 'ya_empezo'


def test_no_se_puede_unir_a_una_sala_que_se_cerro(salas):
    codigo = salas.crear('ana').codigo
    salas.rendirse(codigo, 'ana')

    assert _error(lambda: salas.unirse(codigo, 'beto')).codigo == 'ya_empezo'


def test_empezar_con_un_solo_jugador_no_se_puede(salas):
    codigo = salas.crear('ana').codigo

    error = _error(lambda: salas.empezar(codigo, 'ana'))

    assert (error.codigo, error.estado_http) == ('pocos_jugadores', 409)
    assert salas._salas[codigo].estado == ESPERANDO


def test_empezar_con_dos_si_se_puede(salas):
    codigo = armar_sala(salas, ['ana', 'beto'])

    assert salas.empezar(codigo, 'ana').estado == PREPARANDO


def test_empezar_con_seis_si_se_puede(salas):
    codigo = armar_sala(salas, [f'j{n}' for n in range(1, 7)])

    assert salas.empezar(codigo, 'j1').estado == PREPARANDO


def test_solo_el_anfitrion_empieza_y_elige_el_mapa(salas):
    codigo = armar_sala(salas, ['ana', 'beto'])

    assert _error(lambda: salas.empezar(codigo, 'beto')).codigo == 'no_eres_anfitrion'
    assert _error(lambda: salas.elegir_mapa(codigo, 'beto', 3)).codigo == 'no_eres_anfitrion'


def test_quien_no_esta_en_la_sala_no_puede_hacer_nada(salas):
    codigo = armar_sala(salas, ['ana', 'beto'])

    for accion in (
        lambda: salas.empezar(codigo, 'intruso'),
        lambda: salas.elegir_mapa(codigo, 'intruso', 1),
        lambda: salas.rendirse(codigo, 'intruso'),
        lambda: salas.estado(codigo, 'intruso'),
    ):
        error = _error(accion)
        assert (error.codigo, error.estado_http) == ('no_eres_parte', 403)


@pytest.mark.parametrize('nivel', [0, 5, -1, '2', None, 2.5, True, [], {}])
def test_un_mapa_que_no_existe_se_rechaza(salas, nivel):
    codigo = salas.crear('ana').codigo

    assert _error(lambda: salas.elegir_mapa(codigo, 'ana', nivel)).codigo == 'mapa_invalido'
    assert salas._salas[codigo].nivel == 1


def test_el_mapa_no_se_puede_cambiar_despues_de_empezar(salas):
    codigo = armar_sala(salas, ['ana', 'beto'])
    salas.empezar(codigo, 'ana')

    assert _error(lambda: salas.elegir_mapa(codigo, 'ana', 3)).codigo == 'estado_incorrecto'


def test_un_jugador_que_sale_del_lobby_libera_su_lugar(salas):
    codigo = salas.crear('j1').codigo
    for n in range(2, 7):
        salas.unirse(codigo, f'j{n}')

    salas.rendirse(codigo, 'j6')
    salas.unirse(codigo, 'nuevo')

    assert len(salas._salas[codigo].jugadores) == 6


def test_si_el_anfitrion_sale_del_lobby_la_sala_se_cierra(salas):
    codigo = armar_sala(salas, ['ana', 'beto', 'carla'])

    salas.rendirse(codigo, 'ana')

    sala = salas._salas[codigo]
    assert sala.estado == TERMINADA
    assert sala.motivo == SALA_CERRADA
    resultado = salas.estado(codigo, 'beto')['resultado']
    # No hubo partida: nadie gana, y el motivo no es "ganan los demás".
    assert resultado['motivo'] == SALA_CERRADA
    assert resultado['ganadores'] == []
    # Los demás quedan libres para entrar a otra sala.
    assert salas.sala_de('beto') is None


def test_salirse_de_un_lobby_dos_veces_no_rompe_nada(salas):
    codigo = armar_sala(salas, ['ana', 'beto'])
    salas.rendirse(codigo, 'beto')

    assert _error(lambda: salas.rendirse(codigo, 'beto')).codigo == 'no_eres_parte'


def test_un_registro_nuevo_no_conoce_las_salas_de_otro(reloj, dados):
    una = Salas(reloj=reloj, tirar_dado=dados)
    codigo = una.crear('ana').codigo

    otra = Salas(reloj=reloj, tirar_dado=dados)  # es lo que pasa al reiniciar el servidor

    assert _error(lambda: otra.estado(codigo, 'ana')).codigo == 'sala_no_existe'
