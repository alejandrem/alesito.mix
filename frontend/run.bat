@echo off
title alesito.mix — Transcriptor de Audio a MIDI
echo ============================================
echo   alesito.mix
echo   Transcriptor de Audio a MIDI
echo ============================================
echo holaaa gracias por usar alesito.mix jjaja power by alejandro eliosa morales
echo.

:: Buscar Python (priorizar Python 3.10)
set PYTHON_CMD=
py -3.10 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3.10
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python no encontrado en PATH.
    echo Descarga Python 3.10 desde: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Verificar version de Python
%PYTHON_CMD% -c "import sys; v=sys.version_info; print(f'Python {v.major}.{v.minor}.{v.micro}')" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo verificar la version de Python.
    pause
    exit /b 1
)

:: Verificar dependencias
echo Verificando dependencias...
%PYTHON_CMD% -c "import PyQt6" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] PyQt6 no encontrado. Instalando...
    %PYTHON_CMD% -m pip install PyQt6
)

%PYTHON_CMD% -c "import basic_pitch" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] basic-pitch no encontrado. Instalando...
    %PYTHON_CMD% -m pip install basic-pitch
)

%PYTHON_CMD% -c "import pretty_midi" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] pretty_midi no encontrado. Instalando...
    %PYTHON_CMD% -m pip install pretty_midi
)

%PYTHON_CMD% -c "import importlib.util; import sys; sys.exit(0 if importlib.util.find_spec('fluidsynth') else 1)" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] pyfluidsynth no encontrado. Instalando...
    %PYTHON_CMD% -m pip install pyfluidsynth
)

echo.
echo Iniciando alesito.mix...
echo Presiona ESC para salir del fullscreen.
echo.

:: Ejecutar
echo [INFO] No encontramos modulos CUDA, asi que usaremos la CPU para la IA uwu
set TF_CPP_MIN_LOG_LEVEL=3
%PYTHON_CMD% core\main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La app termino con errores.
    pause
)
