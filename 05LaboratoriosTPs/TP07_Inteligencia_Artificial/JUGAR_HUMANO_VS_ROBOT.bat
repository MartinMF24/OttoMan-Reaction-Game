@echo off
REM ============================================================
REM  DUELO DE REFLEJOS EN VIVO — HUMANO vs ROBOT UNITREE G1
REM ============================================================
cd /d "%~dp0"

echo ============================================================
echo    DUELO DE REFLEJOS EN VIVO — HUMANO vs ROBOT UNITREE G1
echo ============================================================
echo.
echo    INSTRUCCIONES DE JUEGO:
echo      - La camara inicia de frente a las luces con el robot detras.
echo      - Cuenta atras inicial de 5 a 0 para prepararte.
echo      - Teclas [1] [2] [3] [4] [5] [6] de IZQUIERDA a DERECHA:
echo.
echo          [1]          [2]           [3]           [4]           [5]          [6]
echo       Ext. Izq     Arr. Izq     Abj. Cen-Izq  Abj. Cen-Der    Arr. Der     Ext. Der
echo.
echo ============================================================
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
echo    Selecciona el nivel del Robot:
echo      1)  Medio (Competitivo - Balanceado)
echo      2)  Facil (Entrenamiento para practicar teclas)
echo      3)  Dificil (Premier League - Reflejos profesionales)
echo.
set OPDIF=1
set /p OPDIF="   Elegi nivel [1]: "

set DIFICULTAD=medio
if "%OPDIF%"=="1" set DIFICULTAD=medio
if "%OPDIF%"=="2" set DIFICULTAD=facil
if "%OPDIF%"=="3" set DIFICULTAD=dificil

echo.
echo    Iniciando Duelo Humano vs Robot G1...
echo    Coloca tus dedos sobre las teclas 1, 2, 3, 4, 5, 6.
echo.
call EJECUTAR_MI_CODIGO.bat mi_desarrollo\juego_humano_vs_robot.py --duracion %SEGUNDOS% --dificultad %DIFICULTAD%

