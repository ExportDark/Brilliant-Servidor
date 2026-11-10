@echo off
rem Levanta el servidor de cuentas de Brilliant con HTTPS en el puerto 8443, y
rem lo anuncia en la red para que la app lo encuentre sola.
rem La primera vez crea el entorno de Python e instala los paquetes.
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    python -m venv .venv || goto :error
)
rem zeroconf, sin sus partes compiladas (ver requirements.txt).
set SKIP_CYTHON=1
.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt || goto :error
.venv\Scripts\python.exe manage.py migrate --noinput || goto :error
rem Las sesiones sobreviven a un reinicio (estan en la base): se cierran todas.
.venv\Scripts\python.exe manage.py cerrar_sesiones || goto :error

:levantar
.venv\Scripts\python.exe generar_certificados.py || goto :error
echo.
echo Servidor de cuentas en https://localhost:8443  (Ctrl+C para detenerlo)
.venv\Scripts\python.exe servir.py
rem servir.py termina con 3 si la PC cambio de red: se vuelve a levantar con un
rem certificado y un anuncio para la red nueva.
if errorlevel 3 goto :levantar
if errorlevel 1 goto :error
goto :eof

:error
echo No se pudo levantar el servidor.
rem Con doble clic la ventana se cerraria antes de leer el error.
echo %cmdcmdline% | find /i "%~0" >nul && pause
exit /b 1
