@echo off
REM Script de actualización manual de contexto del software.md en Windows
echo [ClassForge] Actualizando documento 'contexto del software.md'...
python "%~dp0update_software_context.py" %*
if %ERRORLEVEL% EQU 0 (
    echo [ClassForge] Documento actualizado correctamente.
) else (
    echo [ClassForge] Ocurrio un error al actualizar el documento.
)
pause
