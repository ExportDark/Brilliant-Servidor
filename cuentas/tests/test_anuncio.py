import socket
import threading
from types import SimpleNamespace

import servir


def test_anuncia_el_servicio_brilliant_con_las_ips_y_el_puerto():
    anuncio = servir.informacion_del_servicio(['192.168.137.252', '10.22.13.30'], 'ORION')

    assert anuncio.type == '_brilliant._tcp.local.'
    assert anuncio.name == 'Brilliant en ORION._brilliant._tcp.local.'
    assert anuncio.port == 8443
    assert [socket.inet_ntoa(ip) for ip in anuncio.addresses] == ['192.168.137.252', '10.22.13.30']


def test_si_la_pc_cambia_de_red_pide_volver_a_levantar_el_servidor(monkeypatch):
    monkeypatch.setattr(servir, 'INTERVALO', 0.01)
    monkeypatch.setattr(servir, 'ips_para_la_app', lambda: ['10.0.0.7'])
    servidor = SimpleNamespace(should_exit=False)
    cambio = threading.Event()

    servir._vigilar_la_red(['192.168.137.252'], servidor, cambio)

    assert cambio.is_set()
    assert servidor.should_exit


def test_si_la_red_no_cambia_no_toca_nada(monkeypatch):
    monkeypatch.setattr(servir, 'INTERVALO', 0.01)
    monkeypatch.setattr(servir, 'ips_para_la_app', lambda: ['192.168.137.252'])
    servidor = SimpleNamespace(should_exit=False)
    cambio = threading.Event()
    # Se detiene desde afuera después de unas cuantas vueltas.
    threading.Timer(0.1, lambda: setattr(servidor, 'should_exit', True)).start()

    servir._vigilar_la_red(['192.168.137.252'], servidor, cambio)

    assert not cambio.is_set()
