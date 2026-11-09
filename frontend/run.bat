@echo off
title alesito.mix ? Transcriptor de Audio a MIDI
cd /d "%~dp0"
echo ============================================
echo   alesito.mix
echo   Transcriptor de Audio a MIDI
echo ============================================
echo holaaa gracias por usar alesito.mix jjaja power by alejandro eliosa morales
echo.

set "PROJECT_ROOT=%~dp0.."
set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"

:: 1. Priorizar el entorno virtual .venv del proyecto si ya existe
if exist "%VENV_PYTHON%" (
    set "PYTHON_CMD=%VENV_PYTHON%"
    goto :python_found
)

:: 2. Buscar Python 3.10 en ubicaciones comunes o py launcher
set PYTHON_CMD=

py -3.10 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.10"
    goto :create_venv
)

if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :create_venv
)

if exist "%ProgramFiles%\Python310\python.exe" (
    set "PYTHON_CMD=%ProgramFiles%\Python310\python.exe"
    goto :create_venv
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :create_venv
)

py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto :create_venv
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python no encontrado en PATH.
    echo Descarga Python 3.10 desde: https://www.python.org/downloads/
    pause
    exit /b 1
)

:create_venv
:: Crear .venv autom?ticamente si no existe
if not exist "%VENV_PYTHON%" (
    echo [INFO] Creando entorno virtual .venv con %PYTHON_CMD%...
    %PYTHON_CMD% -m venv "%PROJECT_ROOT%\.venv"
    if exist "%VENV_PYTHON%" (
        set "PYTHON_CMD=%VENV_PYTHON%"
        echo [INFO] Instalando dependencias en el entorno virtual...
        "%PYTHON_CMD%" -m pip install -r "%PROJECT_ROOT%\requirements.txt"
    )
)

:python_found
:: Verificar version de Python
"%PYTHON_CMD%" -c "import sys; v=sys.version_info; print(f'Python {v.major}.{v.minor}.{v.micro}')" 2>nul
if errorlevel 1 (
    echo [ERROR] No se pudo verificar la version de Python.
    pause
    exit /b 1
)

:: Verificar dependencias clave
echo Verificando dependencias...
"%PYTHON_CMD%" -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo [INFO] PyQt6 no encontrado. Instalando...
    "%PYTHON_CMD%" -m pip install PyQt6
)

"%PYTHON_CMD%" -c "import basic_pitch" 2>nul
if errorlevel 1 (
    echo [INFO] basic-pitch no encontrado. Instalando...
    "%PYTHON_CMD%" -m pip install basic-pitch
)

"%PYTHON_CMD%" -c "import pretty_midi" 2>nul
if errorlevel 1 (
    echo [INFO] pretty_midi no encontrado. Instalando...
    "%PYTHON_CMD%" -m pip install pretty_midi
)

"%PYTHON_CMD%" -c "import importlib.util; import sys; sys.exit(0 if importlib.util.find_spec('fluidsynth') else 1)" 2>nul
if errorlevel 1 (
    echo [INFO] pyfluidsynth no encontrado. Instalando...
    "%PYTHON_CMD%" -m pip install pyfluidsynth
)

echo.
echo Iniciando alesito.mix...
echo Presiona ESC para salir del fullscreen.
echo.

:: Ejecutar
echo [INFO] No encontramos modulos CUDA, asi que usaremos la CPU para la IA uwu
set TF_CPP_MIN_LOG_LEVEL=3
"%PYTHON_CMD%" core\main.py

if errorlevel 1 (
    echo.
    echo [ERROR] La app termino con errores.
    pause
)
