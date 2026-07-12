#!/bin/bash
# Configurar el título del terminal
echo -ne "\033]0;alesito.mix — Transcriptor de Audio a MIDI\007"

echo "============================================"
echo "  alesito.mix"
echo "  Transcriptor de Audio a MIDI"
echo "============================================"
echo "holaaa gracias por usar alesito.mix jjaja power by alejandro eliosa morales"
echo ""

# Buscar Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python no encontrado en PATH."
    read -p "Presiona Enter para continuar..."
    exit 1
fi

PYTHON_CMD="python3"
PIP_CMD="pip3"

# Verificar version de Python
$PYTHON_CMD -c "import sys; v=sys.version_info; print(f'Python {v.major}.{v.minor}.{v.micro}')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] No se pudo verificar la version de Python."
    read -p "Presiona Enter para continuar..."
    exit 1
fi

# =========================================================================
# EN LINUX NO SE PUEDE HACER PIP INSTALL GLOBAL, ASÍ QUE CREAMOS UN VENV
# =========================================================================
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$DIR")"
VENV_DIR="$PROJECT_ROOT/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Creando entorno virtual local para no romper tu Linux..."
    $PYTHON_CMD -m venv --system-site-packages "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
# =========================================================================

echo "Verificando dependencias..."

python -c "import PyQt6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[INFO] PyQt6 no encontrado. Instalando..."
    pip install PyQt6
fi

python -c "import basic_pitch" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[INFO] basic-pitch no encontrado. Instalando..."
    pip install basic-pitch
fi

python -c "import pretty_midi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[INFO] pretty_midi no encontrado. Instalando..."
    pip install pretty_midi
fi

python -c "import importlib.util; import sys; sys.exit(0 if importlib.util.find_spec('fluidsynth') else 1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[INFO] pyfluidsynth no encontrado. Instalando..."
    pip install pyfluidsynth
fi

echo ""
echo "Iniciando alesito.mix..."
echo "Presiona ESC para salir del fullscreen."
echo ""

# Ejecutar
echo "[INFO] No encontramos modulos CUDA, asi que usaremos la CPU para la IA uwu"
export TF_CPP_MIN_LOG_LEVEL=3
python "$DIR/core/main.py"

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] La app termino con errores."
    read -p "Presiona Enter para continuar..."
fi

deactivate
