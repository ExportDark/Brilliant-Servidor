"""Genera los certificados para servir la API con HTTPS en la red local.

- Una **autoridad certificadora local**, que se crea una sola vez y dura 10 años.
  Su certificado público se copia a la app (`assets/certificados/brilliant_ca.pem`),
  que solo confía en ella para hablar con el servidor.
- El **certificado del servidor**, firmado por esa autoridad, para `localhost`,
  `127.0.0.1`, `10.0.2.2` (el emulador de Android) y las IPs de todas las
  interfaces encendidas de esta PC. Se vuelve a generar cada vez: si cambia la
  IP, basta con volver a correr el script, y como la autoridad es la misma, la
  app no hay que recompilarla.

Al final muestra la dirección de la PC, por si la app no encuentra el servidor sola
y hay que escribirla en "Iniciar sesión" > Servidor.

Las claves privadas se quedan en `servidor/certificados/` y no se suben al repo.

Uso: python generar_certificados.py [IP extra ...]
"""

import ipaddress
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from red_local import ips_de_esta_pc, ips_para_la_app

AQUI = Path(__file__).resolve().parent
CARPETA = AQUI / 'certificados'
CA_CERTIFICADO = CARPETA / 'ca.pem'
CA_CLAVE = CARPETA / 'ca.key'
SERVIDOR_CERTIFICADO = CARPETA / 'servidor.pem'
SERVIDOR_CLAVE = CARPETA / 'servidor.key'
EN_LA_APP = AQUI.parent / 'assets' / 'certificados' / 'brilliant_ca.pem'


def _guardar_clave(clave, archivo: Path) -> None:
    archivo.write_bytes(
        clave.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def _autoridad() -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey]:
    """La autoridad local: la de antes si ya existe, o una nueva."""
    if CA_CERTIFICADO.exists() and CA_CLAVE.exists():
        certificado = x509.load_pem_x509_certificate(CA_CERTIFICADO.read_bytes())
        clave = serialization.load_pem_private_key(CA_CLAVE.read_bytes(), password=None)
        return certificado, clave

    clave = ec.generate_private_key(ec.SECP256R1())
    nombre = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Brilliant - autoridad local')])
    ahora = datetime.now(timezone.utc)
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nombre)
        .issuer_name(nombre)
        .public_key(clave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - timedelta(minutes=5))
        .not_valid_after(ahora + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(clave.public_key()), critical=False)
        .sign(clave, hashes.SHA256())
    )
    _guardar_clave(clave, CA_CLAVE)
    CA_CERTIFICADO.write_bytes(certificado.public_bytes(serialization.Encoding.PEM))
    return certificado, clave


def _certificado_del_servidor(ca, ca_clave, ips: list[str]) -> None:
    clave = ec.generate_private_key(ec.SECP256R1())
    ahora = datetime.now(timezone.utc)
    nombres = [x509.DNSName('localhost')] + [
        x509.IPAddress(ipaddress.ip_address(ip)) for ip in ips
    ]
    certificado = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Brilliant - servidor')]))
        .issuer_name(ca.subject)
        .public_key(clave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - timedelta(minutes=5))
        .not_valid_after(ahora + timedelta(days=397))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName(nombres), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_clave.public_key()),
            critical=False,
        )
        .sign(ca_clave, hashes.SHA256())
    )
    _guardar_clave(clave, SERVIDOR_CLAVE)
    SERVIDOR_CERTIFICADO.write_bytes(certificado.public_bytes(serialization.Encoding.PEM))


def main(ips_extra: list[str]) -> None:
    CARPETA.mkdir(exist_ok=True)
    ca, ca_clave = _autoridad()

    ips = list(dict.fromkeys(['127.0.0.1', '10.0.2.2', *ips_de_esta_pc(), *ips_extra]))
    _certificado_del_servidor(ca, ca_clave, ips)

    EN_LA_APP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CA_CERTIFICADO, EN_LA_APP)

    print(f'Certificado del servidor para localhost y {", ".join(ips)}.')
    print(f'La app confía en la autoridad copiada a {EN_LA_APP.relative_to(AQUI.parent)}.')
    para_la_app = ips_para_la_app()
    if para_la_app:
        print()
        print('La app encuentra el servidor sola en la WiFi. Si no lo encuentra, en')
        print('"Iniciar sesión" > Servidor, escribe:')
        for ip in para_la_app:
            print(f'    {ip}')
    else:
        print('Esta PC no está conectada a ninguna red: el celular no la va a encontrar.')


if __name__ == '__main__':
    main(sys.argv[1:])
