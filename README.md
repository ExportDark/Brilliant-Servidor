# Servidor de cuentas de Brilliant

Un programa aparte de la app: guarda las cuentas de los jugadores y les da sesiones.
La app se registra aquí, inicia sesión y puede borrar su cuenta.

Está hecho con paquetes que ya implementan la autenticación, sin sockets a mano:

| Paquete | Para qué |
|---|---|
| Django | Las cuentas (usuario y contraseña), los validadores de contraseña y la base SQLite |
| Django REST framework | La API |
| djoser | Crear la cuenta, verla y borrarla |
| django-rest-knox | Los tokens de sesión |
| argon2-cffi | El hash de las contraseñas (Argon2id) |
| django-cors-headers | Que la versión web de la app pueda llamar a la API |
| uvicorn | Servir la API con HTTPS |
| cryptography | Generar los certificados locales |
| psutil | Saber las IPs de la PC, de todas sus interfaces de red |
| zeroconf | Anunciar el servidor en la red (mDNS), para que la app lo encuentre sola |

## Levantarlo

```bat
servidor\iniciar.bat
```

La primera vez crea el entorno de Python (`servidor\.venv`) e instala los paquetes. Cada vez
aplica las migraciones, vuelve a generar el certificado del servidor, muestra la IP de la PC
y lo levanta en **https://localhost:8443**. Se detiene con Ctrl+C.

- **Desde el emulador de Android**, la app lo encuentra en `https://10.0.2.2:8443`.
- **Desde el celular**, en la misma WiFi que la PC, **la app lo encuentra sola**: el
  servidor se anuncia en la red como "Brilliant en <nombre de la PC>". Si no aparece, en
  "Iniciar sesión" > Servidor se escribe la IP que muestra `iniciar.bat`. La primera vez
  Windows pregunta si deja entrar conexiones: hay que permitirlo en redes privadas.

### Si la PC cambia de red

`servir.py` revisa cada 5 segundos las IPs de la PC. Si cambian (otra WiFi, por ejemplo),
se detiene, e `iniciar.bat` lo vuelve a levantar con un certificado y un anuncio para la
red nueva. La app, al no encontrarlo en la dirección vieja, lo busca en la red y se cambia
sola.

### El anuncio en la red

Es mDNS / DNS-SD, lo mismo con lo que se descubren las impresoras: un servicio
`_brilliant._tcp` con las IPs de la PC y el puerto 8443. Se anuncian las IPs de las
interfaces encendidas, sin las de máquinas virtuales (VMware, VirtualBox, Hyper-V, WSL),
porque el celular no llega a esas.

Anunciarse no le da confianza a nadie: la app igual exige que el certificado sea de la
autoridad de Brilliant. Un servidor ajeno que se anunciara con el mismo nombre no pasaría
de ahí.

> [!note] zeroconf sin partes compiladas
> zeroconf trae DLL compiladas sin firmar, y el Control de Aplicaciones de Windows las
> bloquea ("An Application Control policy has blocked this file"). Por eso se instala en
> Python puro: `requirements.txt` dice `--no-binary zeroconf` e `iniciar.bat` pone
> `SKIP_CYTHON=1`. Es un poco más lento, pero solo anuncia un servicio.

## La API

Todo bajo `/auth/`, en JSON:

| Método y ruta | Qué hace | Cuerpo |
|---|---|---|
| `POST /auth/users/` | Crear la cuenta | `username`, `password`, `re_password` |
| `POST /auth/token/login/` | Iniciar sesión: devuelve `token` y `expiry` | `username`, `password` |
| `GET /auth/users/me/` | Quién soy | — |
| `POST /auth/token/logout/` | Cerrar esta sesión | — |
| `DELETE /auth/users/me/` | Borrar la cuenta | `current_password` |

Las rutas con sesión llevan el header `Authorization: Token <token>`. Los errores vienen en
español, por campo: `{"password": ["Esta contraseña es demasiado corta..."]}`.

Iniciar sesión responde **409** si la cuenta tiene la sesión activa en otro aparato (ver
abajo).

## Las reglas de las cuentas

| Qué | Regla |
|---|---|
| Nombre de usuario | De 3 a 20 caracteres: letras sin acento, números, `.`, `_` y `-`. Se recortan los espacios del borde |
| Mayúsculas | "Ana" y "ana" son la misma cuenta: no se puede crear la otra, y se entra escribiéndola de cualquier forma. El nombre se guarda como se escribió |
| Contraseña | De 8 a 128 caracteres, no común, no solo números y no parecida al usuario. Se recibe tal cual: los espacios del borde son parte de ella, y se aceptan ñ, acentos y emojis |
| Sesiones | Una sola activa por cuenta. Si se usó en otro aparato en los últimos 5 minutos, no deja entrar; si no, la entrada nueva cierra la vieja |

## Qué la hace segura

- **Contraseñas con Argon2id**, nunca en texto. Tienen que tener al menos 8 caracteres, no
  ser comunes, no ser solo números y no parecerse al usuario. Como mucho 128: una
  gigante haría trabajar al servidor calculando su hash.
- **Nombres de usuario sin letras de otros alfabetos**: "аna", con una "а" cirílica, no
  puede hacerse pasar por "ana".
- **Tokens que se guardan con hash** (knox): si se filtrara la base, no servirían. Vencen a
  los 7 días y se renuevan al usarse. Cerrar sesión invalida el token, y borrar la cuenta
  borra todos.
- **Borrar la cuenta pide la contraseña actual**, aunque haya sesión abierta.
- **Nadie ve ni toca la cuenta de otro**: solo existen las rutas `me`.
- **Límite de intentos por IP**: 5 inicios de sesión por minuto y 10 cuentas nuevas por
  hora.
- **Siempre HTTPS**, con una autoridad certificadora local (ver abajo). La app solo confía
  en esa autoridad.
- La `SECRET_KEY` se genera la primera vez en `servidor\.env`, que no se sube al repo.
  `DEBUG` está apagado.

## Los certificados

`generar_certificados.py` crea en `servidor\certificados\`:

- una **autoridad local** (`ca.pem` y `ca.key`), una sola vez, que dura 10 años;
- el **certificado del servidor** (`servidor.pem` y `servidor.key`), para `localhost`,
  `127.0.0.1`, `10.0.2.2` y las IPs de todas las interfaces encendidas de la PC (las
  detecta `red_local.py`). Se regenera cada vez que se levanta el servidor, así que sigue
  sirviendo aunque cambie la IP.

Copia el certificado **público** de la autoridad a la app
(`assets\certificados\brilliant_ca.pem`). Las claves privadas nunca salen de esta PC ni se
suben al repo.

**Para usar la versión web en tu navegador**, el navegador tiene que confiar en la
autoridad local. Se importa `servidor\certificados\ca.pem` en "Entidades de certificación
raíz de confianza" del usuario de Windows (abrir el archivo → Instalar certificado). Es
opcional: la app de Android no lo necesita.

## Tests

```bat
cd servidor
.venv\Scripts\python.exe -m pytest
```

76 tests, uno por archivo de `cuentas\tests\` según qué prueban: crear la cuenta, iniciar
sesión, quién soy, cerrar sesión, borrar la cuenta, la privacidad entre cuentas, cómo se
guardan las contraseñas y los tokens, las IPs de la PC y el anuncio en la red.
