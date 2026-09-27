@echo off
echo ========================================================
echo   INICIANDO CLASSFORGE + CLOUDFLARE TUNNEL (MODO NUBE)
echo ========================================================

echo [1/4] Iniciando contenedor MongoDB...
docker start mongo-classforge

echo [2/4] Iniciando Backend FastAPI en puerto 8000...
start "ClassForge Backend" cmd /k "cd /d "%~dp0classforge-backend" && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [3/4] Iniciando Frontend Angular en puerto 4200...
start "ClassForge Frontend" cmd /k "cd /d "%~dp0classforge-frontend" && npm run start"

echo [4/4] Iniciando Cloudflare Tunnel...
echo Esperando 8 segundos a que inicien los servidores...
timeout /t 8 /nobreak >nul
start "Cloudflare Tunnel" cmd /k "cd /d "%~dp0" && cloudflared.exe tunnel --protocol http2 --url http://localhost:4200 --http-host-header "localhost:4200""

echo.
echo Todo ha sido iniciado en ventanas independientes.
echo Revisa la ventana de 'Cloudflare Tunnel' para ver la URL publica https://xxxx.trycloudflare.com
pause
