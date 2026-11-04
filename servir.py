"""Levanta el servidor de cuentas con HTTPS y lo anuncia en la red local.

El anuncio es mDNS / DNS-SD, el mismo mecanismo con el que se descubren las
impresoras: un servicio `_brilliant._tcp` con las IPs y el puerto de esta PC.
La app lo busca y se conecta sola, sin que haya que escribir la IP. Lo hace
el paquete zeroconf.

Mientras corre, revisa cada pocos segundos si cambiaron las IPs de la PC (por
ejemplo, porque se conectó a otra WiFi). Si cambiaron, se detiene con el
código 3, e `iniciar.bat` lo vuelve a levantar con un certificado y un anuncio
para la red nueva.
"""

import socket
import sys
import threading
from pathlib import Path

import uvicorn
from zeroconf import IPVersion, ServiceInfo, Zeroconf

from red_local import ips_para_la_app

AQUI = Path(__file__).resolve().parent
TIPO = '_brilliant._tcp.local.'
PUERTO = 8443

# Cada cuánto se revisa si la PC cambió de red, en segundos.
INTERVALO = 5

# El código con el que termina cuando la red cambió, para que iniciar.bat lo
# vuelva a levantar.
RED_CAMBIADA = 3


def informacion_del_servicio(ips: list[str], nombre_de_la_pc: str) -> ServiceInfo:
    """El anuncio del servidor: "Brilliant en <PC>", con sus IPs y su puerto."""
    nombre = f'Brilliant en {nombre_de_la_pc}'
    return ServiceInfo(
        TIPO,
        f'{nombre}.{TIPO}',
        addresses=[socket.inet_aton(ip) for ip in ips],
        port=PUERTO,
        properties={'version': '1'},
        server=f'{nombre_de_la_pc.lower()}.local.',
    )


def _vigilar_la_red(ips_al_empezar: list[str], servidor: uvicorn.Server, cambio: threading.Event):
    while not servidor.should_exit:
        if cambio.wait(INTERVALO):
            return
        if sorted(ips_para_la_app()) != sorted(ips_al_empezar):
            print('\nLa PC cambió de red: el servidor se vuelve a levantar para la red nueva.')
            cambio.set()
            servidor.should_exit = True


def main() -> int:
    ips = ips_para_la_app()
    servidor = uvicorn.Server(uvicorn.Config(
        'brilliant_servidor.asgi:application',
        host='0.0.0.0',
        port=PUERTO,
        ssl_keyfile=str(AQUI / 'certificados' / 'servidor.key'),
        ssl_certfile=str(AQUI / 'certificados' / 'servidor.pem'),
    ))

    zeroconf = None
    anuncio = None
    if ips:
        zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        anuncio = informacion_del_servicio(ips, socket.gethostname())
        zeroconf.register_service(anuncio)
        print(f'Anunciado en la red como "{anuncio.name.removesuffix("." + TIPO)}": '
              f'la app lo encuentra sola.')
    else:
        print('Esta PC no está en ninguna red: el servidor no se anuncia.')

    cambio = threading.Event()
    vigia = threading.Thread(target=_vigilar_la_red, args=(ips, servidor, cambio), daemon=True)
    vigia.start()
    try:
        servidor.run()
    finally:
        if zeroconf is not None:
            zeroconf.unregister_service(anuncio)
            zeroconf.close()

    return RED_CAMBIADA if cambio.is_set() else 0


if __name__ == '__main__':
    sys.exit(main())
