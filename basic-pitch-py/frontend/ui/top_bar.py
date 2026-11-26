"""
top_bar.py — Barra superior colapsable con waveform seek, tiempo y ±5s.
Aparece al hacer hover en la parte superior de la ventana.
"""

import numpy as np
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QRectF,
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QLinearGradient, QFont, QMouseEvent, QPaintEvent,
)
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
)

from ui.styles import (
    COLOR_BG_DARK, COLOR_GOLD, COLOR_GOLD_BRIGHT, COLOR_GOLD_DIM,
    COLOR_BTN_PRIMARY, COLOR_WOOD_BORDER, COLOR_WOOD_LIGHT,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, FONT_UI,
)

TOP_BAR_HEIGHT = 42
TOP_BAR_HIDDEN_MARGIN = 4
HOVER_TRIGGER_ZONE = 50


def _fmt_time(seconds: float) -> str:
    """Formatea segundos a 'M:SS'."""
    if seconds < 0:
        seconds = 0
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


# ── WaveformWidget ────────────────────────────────────────────────────────────

class WaveformWidget(QWidget):
    """
    Widget custom que dibuja la envolvente de amplitud del audio.
    Sirve como barra de seek: click/drag para mover la posición.
    """

    seek_requested = pyqtSignal(float)  # posición en segundos

    # Colores
    WAVE_COLOR = QColor(COLOR_GOLD)
    WAVE_COLOR_DIM = QColor(COLOR_GOLD_DIM)
    PROGRESS_COLOR = QColor(COLOR_GOLD_BRIGHT)
    PLAYHEAD_COLOR = QColor(COLOR_GOLD)
    BG_COLOR = QColor(COLOR_BG_DARK)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._waveform_data: np.ndarray | None = None
        self._duration: float = 0.0
        self._current_time: float = 0.0
        self._dragging: bool = False
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def set_waveform(self, data: np.ndarray, duration: float):
        """Recibe array de amplitudes (0-1) y duración en segundos."""
        self._waveform_data = data
        self._duration = duration
        self.update()

    def update_position(self, current_time: float):
        self._current_time = current_time
        self.update()

    def _time_from_x(self, x: float) -> float:
        w = self.width()
        if w <= 0 or self._duration <= 0:
            return 0.0
        ratio = max(0.0, min(x / w, 1.0))
        return ratio * self._duration

    def _x_from_time(self, t: float) -> float:
        if self._duration <= 0:
            return 0.0
        return (t / self._duration) * self.width()

    # ── Mouse events ──────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            pos = self._time_from_x(event.position().x())
            self.seek_requested.emit(pos)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            pos = self._time_from_x(event.position().x())
            self.seek_requested.emit(pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    # ── Paint ─────────────────────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        mid_y = h / 2.0

        # Fondo
        p.fillRect(0, 0, w, h, self.BG_COLOR)

        if self._waveform_data is None or self._duration <= 0:
            # Sin datos: línea horizontal sutil
            p.setPen(QPen(self.WAVE_COLOR_DIM, 1))
            p.drawLine(0, int(mid_y), w, int(mid_y))
            p.end()
            return

        data = self._waveform_data
        n = len(data)
        bar_w = max(1.0, w / n)
        playhead_x = self._x_from_time(self._current_time)

        # Dibujar waveform
        for i in range(n):
            x = (i / n) * w
            amp = float(data[i])
            bar_h = max(1.0, amp * (h - 4) / 2.0)

            # Color: antes del playhead = bright, después = dim
            if x + bar_w <= playhead_x:
                color = self.PROGRESS_COLOR
            else:
                color = self.WAVE_COLOR_DIM

            pen = QPen(color, max(1.0, bar_w - 0.5))
            p.setPen(pen)
            # Línea desde centro hacia arriba y hacia abajo
            x_int = int(x + bar_w / 2)
            p.drawLine(x_int, int(mid_y - bar_h), x_int, int(mid_y + bar_h))

        # Playhead
        ph_x = int(playhead_x)
        p.setPen(QPen(self.PLAYHEAD_COLOR, 2))
        p.drawLine(ph_x, 0, ph_x, h)

        # Dot en el playhead
        p.setBrush(self.PLAYHEAD_COLOR)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(ph_x - 3, int(mid_y) - 3, 6, 6)

        p.end()


# ── TopBar ────────────────────────────────────────────────────────────────────

class TopBar(QWidget):
    """
    Barra superior colapsable.
    - WaveformWidget como seek bar
    - Labels de tiempo
    - Botones ±5s
    - Se muestra/oculta con hover
    """

    seek_requested = pyqtSignal(float)
    skip_requested = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("top_bar")
        self.setMaximumHeight(0)  # Oculta por defecto (altura 0)
        self._expanded = False
        self._duration = 0.0
        self._current_time = 0.0
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(250)
        self._hover_timer.timeout.connect(self._collapse)

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # Labels de tiempo
        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setObjectName("topbar_time")
        self._time_label.setStyleSheet(
            f"color: {COLOR_GOLD}; font-family: 'JetBrains Mono', 'SF Mono', monospace; "
            f"font-size: 11px; font-weight: 600; background: transparent;"
        )
        self._time_label.setFixedWidth(100)

        # Waveform
        self._waveform = WaveformWidget()
        self._waveform.seek_requested.connect(self.seek_requested.emit)

        # Botón -5s
        self._btn_minus = QPushButton("-5s")
        self._btn_minus.setObjectName("topbar_skip")
        self._btn_minus.setFixedSize(40, 24)
        self._btn_minus.setStyleSheet(self._skip_btn_qss())
        self._btn_minus.clicked.connect(lambda: self.skip_requested.emit(-5.0))

        # Botón +5s
        self._btn_plus = QPushButton("+5s")
        self._btn_plus.setObjectName("topbar_skip")
        self._btn_plus.setFixedSize(40, 24)
        self._btn_plus.setStyleSheet(self._skip_btn_qss())
        self._btn_plus.clicked.connect(lambda: self.skip_requested.emit(5.0))

        layout.addWidget(self._time_label)
        layout.addWidget(self._waveform, 1)
        layout.addWidget(self._btn_minus)
        layout.addWidget(self._btn_plus)

        self.setStyleSheet(self._bar_qss())

    # ── Public API ────────────────────────────────────────────────────────

    def set_waveform(self, data: np.ndarray, duration: float):
        self._duration = duration
        self._waveform.set_waveform(data, duration)
        self._update_time_label()

    def update_position(self, current_time: float, duration: float = None):
        self._current_time = current_time
        if duration is not None:
            self._duration = duration
        self._waveform.update_position(current_time)
        self._update_time_label()

    def _update_time_label(self):
        self._time_label.setText(f"{_fmt_time(self._current_time)} / {_fmt_time(self._duration)}")

    # ── Hover expand/collapse ─────────────────────────────────────────────

    def expand(self):
        if self._expanded:
            return
        self._expanded = True
        self._hover_timer.stop()
        anim = QPropertyAnimation(self, b"maximumHeight")
        anim.setDuration(200)
        anim.setStartValue(0)
        anim.setEndValue(TOP_BAR_HEIGHT)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._anim = anim  # keep reference
        self.show()  # Asegurar que sea visible para que enterEvent funcione

    def collapse(self):
        if not self._expanded:
            return
        self._expanded = False
        anim = QPropertyAnimation(self, b"maximumHeight")
        anim.setDuration(250)
        anim.setStartValue(TOP_BAR_HEIGHT)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.start()
        self._anim = anim

    def _collapse(self):
        # Called by timer — only collapse if mouse is not over us
        if not self._expanded:
            return
        # Check if mouse is still in the widget
        cursor_pos = self.mapFromGlobal(self.cursor().pos())
        if not self.rect().contains(cursor_pos):
            self.collapse()

    def enterEvent(self, event):
        self._hover_timer.stop()
        self.expand()

    def leaveEvent(self, event):
        self._hover_timer.start()

    # ── QSS ───────────────────────────────────────────────────────────────

    @staticmethod
    def _bar_qss() -> str:
        return f"""
            #top_bar {{
                background-color: {COLOR_BG_DARK};
                border-bottom: 1px solid {COLOR_WOOD_BORDER};
                border-radius: 0px;
            }}
        """

    @staticmethod
    def _skip_btn_qss() -> str:
        return f"""
            QPushButton {{
                background-color: {COLOR_BTN_PRIMARY};
                color: {COLOR_GOLD};
                border: 1px solid {COLOR_WOOD_BORDER};
                border-radius: 12px;
                font-size: 10px;
                font-weight: 600;
                font-family: '{FONT_UI}', sans-serif;
            }}
            QPushButton:hover {{
                background-color: {COLOR_WOOD_LIGHT};
                border-color: {COLOR_GOLD_DIM};
                color: {COLOR_GOLD_BRIGHT};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_BG_DARK};
            }}
        """
