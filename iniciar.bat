@echo off
rem Levanta el servidor de cuentas de Brilliant con HTTPS en el puerto 8443.
rem La primera vez crea el entorno de Python e instala los paquetes.
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    python -m venv .venv || goto :error
)
.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt || goto :error
.venv\Scripts\python.exe manage.py migrate --noinput || goto :error
.venv\Scripts\python.exe generar_certificados.py || goto :error

echo.
echo Servidor de cuentas en https://localhost:8443  (Ctrl+C para detenerlo)
.venv\Scripts\python.exe -m uvicorn brilliant_servidor.asgi:application --host 0.0.0.0 --port 8443 --ssl-keyfile certificados\servidor.key --ssl-certfile certificados\servidor.pem
goto :eof

:error
echo No se pudo levantar el servidor.
exit /b 1
