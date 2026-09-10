@echo off
REM Inicia el MODO COMPETENCIA DE REFLEJOS entre 2 robots Unitree G1 (Azul vs Rojo).
cd /d "%~dp0"

echo ============================================================
echo    MODO COMPETENCIA DE REFLEJOS — 2 ROBOTS UNITREE G1
echo    ROBOT AZUL vs ROBOT ROJO (DUELO 1 VS 1)
echo ============================================================
echo.
echo    Selecciona la duracion del match:
echo.
echo      1)  30 segundos  (Match rapido)
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
echo    Iniciando arena de competencia Robot Azul vs Robot Rojo...
echo.
call EJECUTAR_MI_CODIGO.bat mi_desarrollo\juego_competencia.py --duracion %SEGUNDOS%
