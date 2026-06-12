@echo off
title alesito.mix — Transcriptor de Audio a MIDI
echo ============================================
echo   alesito.mix
echo   Transcriptor de Audio a MIDI
echo ============================================
echo holaaa gracias por usar alesito.mix jjaja power by alejandro eliosa morales
echo.

:: Buscar Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado en PATH.
    echo Descarga Python 3.10 desde: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Verificar version de Python
python -c "import sys; v=sys.version_info; print(f'Python {v.major}.{v.minor}.{v.micro}')" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo verificar la version de Python.
    pause
    exit /b 1
)

:: Verificar dependencias
echo Verificando dependencias...
python -c "import PyQt6" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] PyQt6 no encontrado. Instalando...
    pip install PyQt6
)

python -c "import basic_pitch" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] basic-pitch no encontrado. Instalando...
    pip install basic-pitch
)

python -c "import pretty_midi" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] pretty_midi no encontrado. Instalando...
    pip install pretty_midi
)

python -c "import importlib.util; import sys; sys.exit(0 if importlib.util.find_spec('fluidsynth') else 1)" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] pyfluidsynth no encontrado. Instalando...
    pip install pyfluidsynth
)

echo.
echo Iniciando alesito.mix...
echo Presiona ESC para salir del fullscreen.
echo.

:: Ejecutar
echo [INFO] No encontramos modulos CUDA, asi que usaremos la CPU para la IA uwu
set TF_CPP_MIN_LOG_LEVEL=3
python core\main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La app termino con errores.
    pause
)
