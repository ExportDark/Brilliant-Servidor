"""Las direcciones de esta PC en la red local.

Las usan el certificado del servidor y `ALLOWED_HOSTS` de Django. Se leen de
las interfaces de red con psutil, y no del nombre de la PC: por el nombre,
Windows no siempre devuelve todas (por ejemplo, la del cable de red).
"""

import ipaddress
import socket

import psutil

# Las interfaces de máquinas virtuales: tienen IP, pero el celular nunca está
# en esas redes.
_VIRTUALES = ('vmware', 'virtualbox', 'vethernet', 'hyper-v', 'wsl', 'loopback')


def _ips(incluir_virtuales: bool) -> list[str]:
    encendidas = {nombre for nombre, estado in psutil.net_if_stats().items() if estado.isup}
    ips = []
    for nombre, direcciones in psutil.net_if_addrs().items():
        if nombre not in encendidas:
            continue
        if not incluir_virtuales and any(v in nombre.lower() for v in _VIRTUALES):
            continue
        for direccion in direcciones:
            if direccion.family != socket.AF_INET:
                continue
            ip = ipaddress.ip_address(direccion.address)
            # 169.254.x.x es la que Windows pone cuando no consigue IP: no sirve.
            if ip.is_loopback or ip.is_link_local:
                continue
            ips.append(direccion.address)
    return ips


def ips_de_esta_pc() -> list[str]:
    """Todas las IPv4 de las interfaces encendidas."""
    return _ips(incluir_virtuales=True)


def ips_para_la_app() -> list[str]:
    """Las que tiene sentido escribir en la app: sin las de máquinas virtuales."""
    return _ips(incluir_virtuales=False)
