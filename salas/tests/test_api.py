"""La API HTTP de las salas: autenticación, códigos de error y una partida de punta a punta
con dos clientes."""

import pytest
from django.contrib.auth import get_user_model
from knox.models import AuthToken
from rest_framework.test import APIClient

from salas import registro as modulo_registro

from .ayudantes import REPARTO

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _registro_de_prueba(salas, monkeypatch):
    """Cada test usa un registro con reloj y dados falsos, vacío."""
    monkeypatch.setattr(modulo_registro, 'registro', salas)


def _cliente(usuario: str) -> APIClient:
    """Un cliente con sesión iniciada como [usuario] (la cuenta se crea si no existe)."""
    cuenta, _ = get_user_model().objects.get_or_create(username=usuario)
    _, token = AuthToken.objects.create(cuenta)
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    return cliente


def _crear(cliente) -> str:
    respuesta = cliente.post('/salas/', format='json')
    assert respuesta.status_code == 201, respuesta.data
    return respuesta.data['codigo']


def test_sin_sesion_ninguna_ruta_de_salas_funciona():
    anonimo = APIClient()

    for metodo, ruta in [
        ('post', '/salas/'),
        ('get', '/salas/ABC234/'),
        ('post', '/salas/ABC234/unirse/'),
        ('post', '/salas/ABC234/mapa/'),
        ('post', '/salas/ABC234/empezar/'),
        ('post', '/salas/ABC234/preparacion/'),
        ('post', '/salas/ABC234/jugada/'),
        ('post', '/salas/ABC234/rendirse/'),
    ]:
        assert getattr(anonimo, metodo)(ruta, format='json').status_code == 401, ruta


def test_con_un_token_inventado_tampoco():
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION='Token ' + 'x' * 64)

    assert cliente.post('/salas/', format='json').status_code == 401


def test_crear_una_sala_responde_201_con_el_codigo_y_la_sala():
    ana = _cliente('ana')

    respuesta = ana.post('/salas/', format='json')

    assert respuesta.status_code == 201
    assert len(respuesta.data['codigo']) == 6
    assert respuesta.data['estado'] == 'esperando'
    assert respuesta.data['anfitrion'] == 'ana'
    assert [j['usuario'] for j in respuesta.data['jugadores']] == ['ana']


def test_crear_otra_sala_estando_en_una_da_409():
    ana = _cliente('ana')
    _crear(ana)

    respuesta = ana.post('/salas/', format='json')

    assert (respuesta.status_code, respuesta.data['codigo']) == (409, 'ya_estas_en_una_sala')


def test_unirse_con_un_codigo_que_no_existe_da_404_con_su_codigo_de_error():
    respuesta = _cliente('beto').post('/salas/ZZZZZZ/unirse/', format='json')

    assert (respuesta.status_code, respuesta.data['codigo']) == (404, 'sala_no_existe')
    assert 'detail' in respuesta.data


def test_unirse_con_el_codigo_y_ver_la_sala():
    ana, beto = _cliente('ana'), _cliente('beto')
    codigo = _crear(ana)

    respuesta = beto.post(f'/salas/{codigo}/unirse/', format='json')

    assert respuesta.status_code == 200
    assert [j['usuario'] for j in respuesta.data['jugadores']] == ['ana', 'beto']
    assert respuesta.data['yo']['usuario'] == 'beto'


def test_la_sala_llena_responde_409(salas):
    codigo = _crear(_cliente('j1'))
    for n in range(2, 7):
        assert _cliente(f'j{n}').post(f'/salas/{codigo}/unirse/', format='json').status_code == 200

    respuesta = _cliente('j7').post(f'/salas/{codigo}/unirse/', format='json')

    assert (respuesta.status_code, respuesta.data['codigo']) == (409, 'sala_llena')


def test_quien_no_es_el_anfitrion_no_puede_empezar_ni_elegir_mapa():
    ana, beto = _cliente('ana'), _cliente('beto')
    codigo = _crear(ana)
    beto.post(f'/salas/{codigo}/unirse/', format='json')

    for ruta, cuerpo in [(f'/salas/{codigo}/empezar/', {}), (f'/salas/{codigo}/mapa/', {'nivel': 2})]:
        respuesta = beto.post(ruta, cuerpo, format='json')
        assert (respuesta.status_code, respuesta.data['codigo']) == (403, 'no_eres_anfitrion')


def test_empezar_con_un_solo_jugador_da_409():
    ana = _cliente('ana')
    codigo = _crear(ana)

    respuesta = ana.post(f'/salas/{codigo}/empezar/', format='json')

    assert (respuesta.status_code, respuesta.data['codigo']) == (409, 'pocos_jugadores')


@pytest.mark.parametrize('cuerpo', [{}, {'nivel': None}, {'nivel': 9}, {'nivel': '2'}, {'nivel': [2]}])
def test_elegir_un_mapa_invalido_da_400(cuerpo):
    ana = _cliente('ana')
    codigo = _crear(ana)

    respuesta = ana.post(f'/salas/{codigo}/mapa/', cuerpo, format='json')

    assert (respuesta.status_code, respuesta.data['codigo']) == (400, 'mapa_invalido')


@pytest.mark.parametrize('cuerpo', [[], 'texto', 5, None])
def test_un_cuerpo_que_no_es_un_objeto_json_se_rechaza_sin_romper_nada(cuerpo):
    ana, beto = _cliente('ana'), _cliente('beto')
    codigo = _crear(ana)
    beto.post(f'/salas/{codigo}/unirse/', format='json')
    ana.post(f'/salas/{codigo}/empezar/', format='json')

    for ruta in ('mapa', 'preparacion', 'jugada'):
        respuesta = ana.post(f'/salas/{codigo}/{ruta}/', cuerpo, format='json')
        assert 400 <= respuesta.status_code < 500, (ruta, respuesta.status_code)


def test_quien_no_esta_en_la_sala_recibe_403_al_preguntar():
    ana = _cliente('ana')
    codigo = _crear(ana)

    respuesta = _cliente('intruso').get(f'/salas/{codigo}/')

    assert (respuesta.status_code, respuesta.data['codigo']) == (403, 'no_eres_parte')


def test_preguntar_con_la_misma_version_responde_304_y_con_otra_el_estado(salas):
    ana, beto = _cliente('ana'), _cliente('beto')
    codigo = _crear(ana)
    version = ana.get(f'/salas/{codigo}/').data['version']

    assert ana.get(f'/salas/{codigo}/?version={version}').status_code == 304

    beto.post(f'/salas/{codigo}/unirse/', format='json')  # algo cambia

    respuesta = ana.get(f'/salas/{codigo}/?version={version}')
    assert respuesta.status_code == 200
    assert respuesta.data['version'] > version
    # Una versión que no es un número se ignora: se responde el estado.
    assert ana.get(f'/salas/{codigo}/?version=abc').status_code == 200


def test_el_304_tambien_cuenta_como_estar_conectado(salas, reloj, dados):
    ana, beto = _cliente('ana'), _cliente('beto')
    codigo = _crear(ana)
    beto.post(f'/salas/{codigo}/unirse/', format='json')
    ana.post(f'/salas/{codigo}/empezar/', format='json')
    version = ana.get(f'/salas/{codigo}/').data['version']

    for _ in range(8):  # 16 segundos preguntando, sin que cambie nada
        reloj.avanzar(2)
        assert ana.get(f'/salas/{codigo}/?version={version}').status_code in (200, 304)
        beto.get(f'/salas/{codigo}/?version={version}')

    assert salas._salas[codigo].jugadores['ana'].estado == 'activo'
    assert salas._salas[codigo].jugadores['beto'].estado == 'activo'


def test_una_partida_de_punta_a_punta_por_http(dados):
    ana, beto = _cliente('ana'), _cliente('beto')
    codigo = _crear(ana)
    assert beto.post(f'/salas/{codigo}/unirse/', format='json').status_code == 200
    assert ana.post(f'/salas/{codigo}/mapa/', {'nivel': 2}, format='json').status_code == 200
    assert ana.post(f'/salas/{codigo}/empezar/', format='json').status_code == 200

    dados.poner(1, 3)
    for cliente in (ana, beto):
        respuesta = cliente.post(f'/salas/{codigo}/preparacion/', {'valores': REPARTO}, format='json')
        assert respuesta.status_code == 200, respuesta.data

    vista = ana.get(f'/salas/{codigo}/').data
    assert (vista['estado'], vista['ronda'], vista['dados']) == ('jugando', 1, [1, 3])
    jugada = next(j for j in vista['yo']['jugadas'] if j['ancla'] == 1)
    assert (jugada['valor'], 'D1' in jugada['casillas']) == (3, True)

    respuesta = ana.post(
        f'/salas/{codigo}/jugada/', {'ronda': 1, 'dado_ancla': 1, 'casilla': 'D1'}, format='json'
    )
    assert respuesta.status_code == 200
    assert respuesta.data['yo']['tablero']['D1'] == 3

    # Un doble toque da 409, no se cuenta dos veces.
    repetida = ana.post(
        f'/salas/{codigo}/jugada/', {'ronda': 1, 'dado_ancla': 1, 'casilla': 'D1'}, format='json'
    )
    assert (repetida.status_code, repetida.data['codigo']) == (409, 'ya_jugaste')

    # Una jugada que no se puede da 400 con el motivo.
    mala = beto.post(
        f'/salas/{codigo}/jugada/', {'ronda': 1, 'dado_ancla': 1, 'casilla': 'G7'}, format='json'
    )
    assert (mala.status_code, mala.data['codigo'], mala.data['motivo']) == (400, 'jugada_invalida', 'sin_vecino')

    # Pasar teniendo jugada da 409.
    pasar = beto.post(f'/salas/{codigo}/jugada/', {'ronda': 1, 'pasar': True}, format='json')
    assert (pasar.status_code, pasar.data['codigo']) == (409, 'tienes_jugada')

    # Beto se rinde: gana ana.
    final = beto.post(f'/salas/{codigo}/rendirse/', format='json')
    assert final.status_code == 200
    assert final.data['estado'] == 'terminada'
    resultado = ana.get(f'/salas/{codigo}/').data['resultado']
    assert resultado['ganadores'] == ['ana']
    assert resultado['motivo'] == 'ultimo_jugador'


def test_el_servidor_nunca_manda_el_tablero_de_otro_por_http(dados):
    ana, beto = _cliente('ana'), _cliente('beto')
    codigo = _crear(ana)
    beto.post(f'/salas/{codigo}/unirse/', format='json')
    ana.post(f'/salas/{codigo}/mapa/', {'nivel': 2}, format='json')
    ana.post(f'/salas/{codigo}/empezar/', format='json')
    dados.poner(1, 3)
    for cliente in (ana, beto):
        cliente.post(f'/salas/{codigo}/preparacion/', {'valores': REPARTO}, format='json')
    ana.post(f'/salas/{codigo}/jugada/', {'ronda': 1, 'dado_ancla': 1, 'casilla': 'D1'}, format='json')

    cuerpo = beto.get(f'/salas/{codigo}/').content.decode()

    assert cuerpo.count('"tablero"') == 1  # solo el de beto
    assert '"D1":3' not in cuerpo.replace(' ', '')  # lo que anotó ana no aparece


def test_el_registro_vacio_tras_un_reinicio_responde_404_no_500():
    codigo = _crear(_cliente('ana'))
    modulo_registro.registro = type(modulo_registro.registro)()  # como reiniciar el servidor

    respuesta = _cliente('ana').get(f'/salas/{codigo}/')

    assert (respuesta.status_code, respuesta.data['codigo']) == (404, 'sala_no_existe')


def test_salirse_del_lobby_responde_bien_aunque_ya_no_se_este_en_la_sala():
    ana, beto = _cliente('ana'), _cliente('beto')
    codigo = _crear(ana)
    beto.post(f'/salas/{codigo}/unirse/', format='json')

    respuesta = beto.post(f'/salas/{codigo}/rendirse/', format='json')

    # Salió bien: no es un error aunque ya no pueda ver la sala.
    assert respuesta.status_code == 204
    assert [j['usuario'] for j in ana.get(f'/salas/{codigo}/').data['jugadores']] == ['ana']
    assert beto.get(f'/salas/{codigo}/').status_code == 403


def test_si_el_anfitrion_sale_del_lobby_ve_la_sala_cerrada():
    ana, beto = _cliente('ana'), _cliente('beto')
    codigo = _crear(ana)
    beto.post(f'/salas/{codigo}/unirse/', format='json')

    respuesta = ana.post(f'/salas/{codigo}/rendirse/', format='json')

    assert respuesta.status_code == 200
    assert respuesta.data['estado'] == 'terminada'
    assert respuesta.data['resultado']['motivo'] == 'anfitrion_se_fue'
