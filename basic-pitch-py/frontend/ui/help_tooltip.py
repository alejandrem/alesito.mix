"""
help_tooltip.py — Popup frameless de ayuda con texto y botón Cerrar.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

from ui.styles import (
    COLOR_WOOD_DARK, COLOR_WOOD_BORDER, COLOR_GOLD,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
)


class HelpTooltip(QWidget):
    """Popup minimalista que muestra texto de ayuda con botón Cerrar."""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Popup
        )
        self.setFixedWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_WOOD_DARK};
                border: 1px solid {COLOR_WOOD_BORDER};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Texto de ayuda
        self._lbl_texto = QLabel()
        self._lbl_texto.setWordWrap(True)
        self._lbl_texto.setStyleSheet(f"""
            color: {COLOR_TEXT_SECONDARY};
            font-size: 10px;
            background: transparent;
            border: none;
            padding: 2px;
        """)
        layout.addWidget(self._lbl_texto)

        # Botón cerrar
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_cerrar = QPushButton("Cerrar")
        self._btn_cerrar.setFixedHeight(24)
        self._btn_cerrar.setMinimumWidth(60)
        self._btn_cerrar.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_GOLD};
                border: 1px solid {COLOR_WOOD_BORDER};
                border-radius: 3px;
                font-size: 11px;
                padding: 2px 10px;
            }}
            QPushButton:hover {{
                border-color: {COLOR_GOLD};
            }}
        """)
        self._btn_cerrar.clicked.connect(self._on_close)
        btn_row.addWidget(self._btn_cerrar)
        layout.addLayout(btn_row)

    def _on_close(self):
        self.hide()
        self.closed.emit()

    def mostrar(self, texto: str, boton_ref: QWidget):
        """Muestra el tooltip debajo del botón referenciado."""
        self._lbl_texto.setText(texto)
        self.adjustSize()
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.adjustSize()

        # Posicionar debajo del botón
        if boton_ref:
            pos = boton_ref.mapToGlobal(boton_ref.rect().bottomLeft())
            self.move(pos.x(), pos.y() + 4)

        self.show()
        self.raise_()
        self.activateWindow()
