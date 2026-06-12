"""
main.py — Entry point de alesito.mix.
Configura sys.path, QApplication y lanza la ventana principal en fullscreen.
"""

import sys
import os
from pathlib import Path

# ── Configurar sys.path para incluir el frontend ────────────────────────
_core_dir = Path(__file__).resolve().parent
_frontend_dir = _core_dir.parent

# Nota: basic-pitch/ se agrega al path desde transcription_worker.py cuando es necesario
if str(_frontend_dir) not in sys.path:
    sys.path.insert(0, str(_frontend_dir))

# ── Configurar búsqueda de DLLs para FluidSynth (Windows Python >= 3.8) ───
if os.name == 'nt':
    assets_dir = _frontend_dir  # Las dlls ahora están en la raíz del frontend
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(str(assets_dir))
        except Exception:
            pass
    os.environ["PATH"] = str(assets_dir) + os.pathsep + os.environ.get("PATH", "")


def main():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont

    # ── Alta resolución ──────────────────────────────────────────────────────
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # ── Aplicar estilos ──────────────────────────────────────────────────────
    from ui.styles import QSS
    app.setStyleSheet(QSS)

    # ── Fuente por defecto ───────────────────────────────────────────────────
    font = QFont("Inter", 10)
    app.setFont(font)

    # ── Ventana principal ────────────────────────────────────────────────────
    from core.app import MainWindow
    window = MainWindow()
    window.showFullScreen()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
