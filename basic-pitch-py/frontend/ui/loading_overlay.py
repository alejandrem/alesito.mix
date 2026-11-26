"""
loading_overlay.py — Popup frameless de carga con mensajes y barra de progreso.
"""

import random
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QFrame,
)

from ui.styles import (
    COLOR_BG_DARKEST, COLOR_WOOD_DARK, COLOR_WOOD_BORDER,
    COLOR_GOLD, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_PROGRESS_BG, COLOR_PROGRESS_FILL, COLOR_BTN_DANGER,
)

MSJESAJES = [
    "Analizando audio...",
    "Detectando notas...",
    "Procesando frecuencias...",
    "Casi listo...",
    "Afinando detalles...",
    "Transcribiendo...",
    "Un momento más...",
    "Casi terminamos...",
]


class LoadingOverlay(QWidget):
    """
    Popup frameless que aparece durante la transcripción.
    Muestra tipo de archivo, mensajes rotativos, barra de progreso y botón cancelar.
    """

    cancel_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog
        )
        self.setFixedSize(440, 180)
        self._setup_ui()
        self._msg_idx = 0

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_WOOD_DARK};
                border: 1px solid {COLOR_WOOD_BORDER};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Tipo de archivo
        self._lbl_tipo = QLabel("Cargando...")
        self._lbl_tipo.setStyleSheet(f"""
            color: {COLOR_GOLD};
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(self._lbl_tipo)

        # Barra de progreso (ancha)
        self._progress = QProgressBar()
        self._progress.setMinimum(0)
        self._progress.setMaximum(100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(8)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLOR_PROGRESS_BG};
                border: 1px solid {COLOR_WOOD_BORDER};
                border-radius: 0px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_PROGRESS_FILL};
                border-radius: 0px;
            }}
        """)
        layout.addWidget(self._progress)

        # Mensaje (abajo de la barra, sin borde)
        self._lblMensaje = QLabel("Preparando...")
        self._lblMensaje.setStyleSheet(f"""
            color: {COLOR_TEXT_SECONDARY};
            font-size: 11px;
        """)
        self._lblMensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lblMensaje)

        # Botón cancelar (abajo de la barra)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_cancel = QPushButton("Cancelar")
        self._btn_cancel.setFixedHeight(24)
        self._btn_cancel.setMinimumWidth(70)
        self._btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_WOOD_BORDER};
                border-radius: 3px;
                font-size: 10px;
                padding: 2px 8px;
            }}
            QPushButton:hover {{
                color: {COLOR_GOLD};
                border-color: {COLOR_GOLD};
            }}
        """)
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._btn_cancel)
        layout.addLayout(btn_row)

        # Timer para mensajes rotativos
        self._msg_timer = QTimer(self)
        self._msg_timer.timeout.connect(self._rotar_mensaje)
        self._msg_timer.setInterval(2000)

    def _rotar_mensaje(self):
        self._msg_idx = (self._msg_idx + 1) % len(MSJESAJES)
        self._lblMensaje.setText(MSJESAJES[self._msg_idx])

    def _on_cancel(self):
        self._msg_timer.stop()
        self.cancel_clicked.emit()
        self.ocultar()

    def mostrar(self, nombre_archivo: str):
        """Muestra el overlay centrado sobre la ventana padre."""
        self._lbl_tipo.setText(f"Cargando ({nombre_archivo})")
        self._lblMensaje.setText(MSJESAJES[0])
        self._msg_idx = 0
        self._progress.setValue(0)
        self._msg_timer.start()

        # Centrar sobre el padre usando coordenadas globales (funciona con multi-monitor)
        if self.parent():
            parent_center = self.parent().rect().center()
            global_center = self.parent().mapToGlobal(parent_center)
            self.move(global_center.x() - self.width() // 2,
                      global_center.y() - self.height() // 2)

        self.show()
        self.raise_()
        self.activateWindow()

    def ocultar(self):
        """Oculta el overlay."""
        self._msg_timer.stop()
        self.hide()

    def set_progreso(self, value: int):
        self._progress.setValue(value)

    def set_mensaje(self, msg: str):
        self._lblMensaje.setText(msg)
