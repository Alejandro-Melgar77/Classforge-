@echo off
echo ========================================================
echo     INICIANDO CLASSFORGE - MODO 100%% LOCAL (OFFLINE)
echo ========================================================

echo [1/3] Iniciando base de datos MongoDB...
docker start mongo-classforge

echo [2/3] Iniciando Backend FastAPI en http://localhost:8000...
start "ClassForge Backend" cmd /k "cd /d "%~dp0classforge-backend" && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [3/3] Iniciando Frontend Angular en http://localhost:4200...
start "ClassForge Frontend" cmd /k "cd /d "%~dp0classforge-frontend" && npm run start"

echo.
echo ========================================================
echo   SISTEMA INICIADO CORRECTAMENTE EN MODO LOCAL
echo ========================================================
echo Abre tu navegador e ingresa a:
echo   http://localhost:4200
echo.
echo Presiona cualquier tecla para cerrar este iniciador...
pause >nul
