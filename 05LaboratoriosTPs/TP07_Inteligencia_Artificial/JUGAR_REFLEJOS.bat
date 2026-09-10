@echo off
REM Inicia el juego de reflejos interactivo 3D con el robot Unitree G1 (6 luces LED).
cd /d "%~dp0"

echo ============================================================
echo    JUEGO DE REFLEJOS — UNITREE G1 (6 LUCES LED)
echo ============================================================
echo.
echo    Selecciona la duracion de la partida:
echo.
echo      1)  30 segundos  (Partida rapida)
echo      2)  60 segundos  (1 minuto)
echo      3)  120 segundos (2 minutos)
echo      4)  Personalizado (ingresar segundos)
echo.
set OPCION=1
set /p OPCION="   Elegi una opcion [1]: "

set SEGUNDOS=30
if "%OPCION%"=="1" set SEGUNDOS=30
if "%OPCION%"=="2" set SEGUNDOS=60
if "%OPCION%"=="3" set SEGUNDOS=120
if "%OPCION%"=="4" (
    set /p SEGUNDOS="   Ingresa la duracion en segundos [30]: "
)

echo.
echo    Queres orden aleatorio o secuencial?
echo      1)  Aleatorio (Mayor desafio de reflejos)
echo      2)  Secuencial (1 al 6 en orden)
echo.
set MODO_ORDEN=1
set /p MODO_ORDEN="   Elegi 1 o 2 [1]: "
set ARGS_EXTRA=--duracion %SEGUNDOS%
if "%MODO_ORDEN%"=="2" set ARGS_EXTRA=%ARGS_EXTRA% --secuencial

echo.
echo    Iniciando juego...
echo.
call EJECUTAR_MI_CODIGO.bat mi_desarrollo\juego_reflejos.py %ARGS_EXTRA%
