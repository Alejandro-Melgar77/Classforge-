@echo off
setlocal enabledelayedexpansion
title ClassForge 2.0 - Local AI Node & Static Tunnel (Liquid AI LFM 1.7B)

echo ==============================================================================
echo   CLASSFORGE 2.0 - NODO DE IA LOCAL Y TUNEL ESTATICO (LIQUID AI LFM 1.7B)
echo ==============================================================================
echo.

:: 1. Dominio Estatico Permanente de ngrok (Fijo, nunca cambia)
set "NGROK_STATIC_DOMAIN=https://repackage-remarry-reviving.ngrok-free.dev"

:: 2. Variables de entorno de Ollama para acceso seguro y cross-origin
set "OLLAMA_ORIGINS=*"
set "OLLAMA_HOST=0.0.0.0:11434"
set "MODEL_NAME=classforge-local-1.7b"
set "OLLAMA_BIN=ollama"

:: Verificar si ollama esta en el PATH o en el directorio estandar
where ollama >nul 2>&1
if errorlevel 1 (
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        set "OLLAMA_BIN=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
        set "PATH=%LOCALAPPDATA%\Programs\Ollama;!PATH!"
    ) else if exist "%ProgramFiles%\Ollama\ollama.exe" (
        set "OLLAMA_BIN=%ProgramFiles%\Ollama\ollama.exe"
        set "PATH=%ProgramFiles%\Ollama;!PATH!"
    ) else (
        echo [!] Ollama no se encuentra en el PATH ni en la ruta predeterminada.
        echo [*] Asegurate de que Ollama este instalado o ejecuta el runtime manualmente.
    )
)

:: 3. Verificar o arrancar daemon de Ollama
echo [1/3] Verificando daemon de Ollama en puerto 11434...
curl.exe -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [*] Iniciando servidor Ollama con OLLAMA_ORIGINS="*" y host 0.0.0.0:11434...
    start "Ollama Engine" cmd /k "!OLLAMA_BIN! serve"
    echo [*] Esperando a que el daemon de Ollama este listo...
    timeout /t 5 /nobreak >nul
) else (
    echo [OK] El daemon de Ollama ya esta en ejecucion y escuchando en el puerto 11434.
)

:: 4. Verificar o compilar modelo especializado classforge-local-1.7b
echo.
echo [2/3] Verificando modelo local: !MODEL_NAME!...
curl.exe -s http://localhost:11434/api/tags | findstr /I "!MODEL_NAME!" >nul 2>&1
if errorlevel 1 (
    echo [*] Modelo !MODEL_NAME! no encontrado en tags locales.
    echo [*] Compilando modelo desde ml/export/Modelfile...
    if exist "ml\export\Modelfile" (
        !OLLAMA_BIN! create !MODEL_NAME! -f ml/export/Modelfile
    ) else (
        echo [!] ml/export/Modelfile no encontrado en el directorio actual.
    )
) else (
    echo [OK] Modelo !MODEL_NAME! disponible y listo para inferencia UML.
)

:: 5. Levantar Tunel HTTPS Fiable
echo.
echo [3/3] Levantando tunel seguro HTTPS permanente hacia http://localhost:11434...

:: Localizar binario de ngrok (PATH, npm global o archivo local)
set "NGROK_BIN="
where ngrok >nul 2>&1
if not errorlevel 1 (
    set "NGROK_BIN=ngrok"
) else if exist "%APPDATA%\npm\ngrok.cmd" (
    set "NGROK_BIN=%APPDATA%\npm\ngrok.cmd"
) else if exist "%LOCALAPPDATA%\npm\ngrok.cmd" (
    set "NGROK_BIN=%LOCALAPPDATA%\npm\ngrok.cmd"
) else if exist "%~dp0ngrok.exe" (
    set "NGROK_BIN=%~dp0ngrok.exe"
)

if defined NGROK_BIN (
    if defined NGROK_STATIC_DOMAIN (
        echo.
        echo ==============================================================================
        echo   TUNEL ESTATICO PERMANENTE ACTIVADO (NGROK)
        echo   URL Fija: !NGROK_STATIC_DOMAIN!
        echo   Esta URL nunca cambiara aunque reinicies o apagues la PC.
        echo ==============================================================================
        echo.
        start "ngrok Static Tunnel - Local AI" cmd /k ""!NGROK_BIN!" http 11434 --url !NGROK_STATIC_DOMAIN!"
        goto :fin
    ) else (
        echo [*] Iniciando ngrok dinamico...
        start "ngrok Tunnel - Local AI" cmd /k ""!NGROK_BIN!" http 11434"
        goto :fin
    )
)

:: Fallback a Cloudflare si ngrok no estuviera disponible
set "CLOUDFLARED_BIN="
if exist "%~dp0cloudflared.exe" (
    set "CLOUDFLARED_BIN=%~dp0cloudflared.exe"
) else if exist ".\cloudflared.exe" (
    set "CLOUDFLARED_BIN=.\cloudflared.exe"
) else (
    where cloudflared >nul 2>&1
    if not errorlevel 1 (
        set "CLOUDFLARED_BIN=cloudflared"
    )
)

if defined CLOUDFLARED_BIN (
    echo [*] Iniciando Cloudflare Tunnel de respaldo con !CLOUDFLARED_BIN!...
    start "Cloudflare Tunnel - Local AI" cmd /k ""!CLOUDFLARED_BIN!" tunnel --url http://localhost:11434 --http-host-header="localhost:11434""
    goto :fin
)

echo.
echo [!] Ni ngrok ni cloudflared fueron encontrados.
echo [*] Puedes conectarte localmente usando: http://localhost:11434

:fin
echo.
echo ==============================================================================
echo   Nodo de IA Local activo con URL estatica:
echo   !NGROK_STATIC_DOMAIN!
echo   Manten esta ventana abierta durante tus sesiones de trabajo.
echo ==============================================================================
pause
