import socket
from types import SimpleNamespace

import pytest

import red_local


@pytest.fixture
def interfaces(monkeypatch):
    """Una PC con Wi-Fi y cable encendidos, una máquina virtual, el cable de
    otra red apagado y una interfaz sin red (169.254)."""

    def direccion(ip):
        return SimpleNamespace(family=socket.AF_INET, address=ip)

    monkeypatch.setattr(red_local.psutil, 'net_if_addrs', lambda: {
        'Wi-Fi': [direccion('192.168.137.252')],
        'Ethernet': [direccion('10.22.13.30')],
        'Ethernet 2': [direccion('172.16.0.8')],
        'VMware Network Adapter VMnet8': [direccion('192.168.83.1')],
        'Conexión de área local* 1': [direccion('169.254.48.108')],
        'Loopback Pseudo-Interface 1': [direccion('127.0.0.1')],
    })
    monkeypatch.setattr(red_local.psutil, 'net_if_stats', lambda: {
        'Wi-Fi': SimpleNamespace(isup=True),
        'Ethernet': SimpleNamespace(isup=True),
        'Ethernet 2': SimpleNamespace(isup=False),
        'VMware Network Adapter VMnet8': SimpleNamespace(isup=True),
        'Conexión de área local* 1': SimpleNamespace(isup=True),
        'Loopback Pseudo-Interface 1': SimpleNamespace(isup=True),
    })


def test_toma_todas_las_interfaces_encendidas_menos_las_sin_red(interfaces):
    # La del cable aparece aunque Windows no la asocie al nombre de la PC.
    assert sorted(red_local.ips_de_esta_pc()) == ['10.22.13.30', '192.168.137.252', '192.168.83.1']


def test_para_la_app_quita_las_maquinas_virtuales(interfaces):
    assert sorted(red_local.ips_para_la_app()) == ['10.22.13.30', '192.168.137.252']
