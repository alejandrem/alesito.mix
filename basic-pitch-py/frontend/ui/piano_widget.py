"""
piano_widget.py — Piano vertical de 88 teclas con iluminación por color de nota.
"""

from PyQt6.QtCore import Qt, QRect, QSize, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QFont
from PyQt6.QtWidgets import QWidget

from ui.styles import (
    PIANO_LOWEST_PITCH, PIANO_HIGHEST_PITCH, PIANO_NUM_KEYS,
    COLOR_KEY_WHITE, COLOR_KEY_WHITE_BOTTOM,
    COLOR_KEY_BLACK, COLOR_KEY_BLACK_BOTTOM,
    COLOR_KEY_BORDER, COLOR_BG_DARKEST,
    NOTE_NAMES, PIANO_WIDGET_WIDTH, KEY_WHITE_HEIGHT,
)


def _is_black(pitch: int) -> bool:
    return (pitch % 12) in (1, 3, 6, 8, 10)


class PianoWidget(QWidget):
    """
    Piano vertical de 88 teclas.
    Notas agudas arriba, graves abajo.
    Las teclas se iluminan con el color de la nota que suena.
    Las negras están a la derecha (tocando el piano roll).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("piano_widget")
        self.setMinimumWidth(PIANO_WIDGET_WIDTH)
        self.setMaximumWidth(PIANO_WIDGET_WIDTH)

        self._active_colors: dict[int, str] = {}
        self._zoom = 1.0
        self._row_height = 0.0
        self._scroll_offset = 0.0  # Offset vertical sincronizado con piano roll
        self._recalc_layout()

    def _recalc_layout(self):
        h = self.height()
        self._row_height = (h / PIANO_NUM_KEYS if h > 0 else 10) * self._zoom

    def set_zoom(self, zoom: float):
        self._zoom = max(1.0, min(zoom, 4.0))
        self._recalc_layout()
        self.update()

    def set_scroll_offset(self, offset: float):
        """Offset vertical del scroll del piano roll para sincronización."""
        self._scroll_offset = offset
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._recalc_layout()

    def sizeHint(self):
        return QSize(PIANO_WIDGET_WIDTH, PIANO_NUM_KEYS * 10)

    # ── Slots ────────────────────────────────────────────────────────────────

    @pyqtSlot(int, int, str)
    def on_note_on(self, pitch: int, velocity: int, color: str):
        if PIANO_LOWEST_PITCH <= pitch <= PIANO_HIGHEST_PITCH:
            self._active_colors[pitch] = color
            self.update()

    @pyqtSlot(int)
    def on_note_off(self, pitch: int):
        self._active_colors.pop(pitch, None)
        self.update()

    def clear_highlights(self):
        self._active_colors.clear()
        self.update()

    # ── Dibujado ─────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        rh = self._row_height

        # Fondo
        painter.fillRect(0, 0, w, h, QColor(COLOR_BG_DARKEST))

        # ── Paso 1: Fondo blanco continuo ────────────────────────────────────
        for i in range(PIANO_NUM_KEYS):
            y = i * rh - self._scroll_offset
            painter.fillRect(QRect(0, int(y), w, int(rh) + 1), QColor(COLOR_KEY_WHITE))

        # ── Paso 2: Teclas blancas (borders + labels + highlight) ────────────
        for pitch in range(PIANO_LOWEST_PITCH, PIANO_HIGHEST_PITCH + 1):
            if _is_black(pitch):
                continue

            idx = pitch - PIANO_LOWEST_PITCH
            y = idx * rh - self._scroll_offset
            rect = QRect(0, int(y), w, int(rh) + 1)

            if pitch in self._active_colors:
                # Highlight con color de la nota
                note_color = QColor(self._active_colors[pitch])
                note_color.setAlpha(180)
                grad = QLinearGradient(0, 0, 0, rh)
                grad.setColorAt(0, note_color.lighter(130))
                grad.setColorAt(1, note_color)
                painter.fillRect(rect, grad)
                painter.setPen(QPen(note_color.darker(120), 1))
                painter.drawRect(rect)
            else:
                painter.setPen(QPen(QColor(COLOR_KEY_BORDER), 1))
                painter.drawRect(rect)

            # Label C de cada octava
            if pitch % 12 == 0:
                octave = (pitch // 12) - 1
                painter.setPen(QColor(COLOR_KEY_BORDER))
                painter.setFont(QFont("Consolas", 7))
                painter.drawText(
                    QRect(2, int(y) + 2, w - 4, int(rh) - 2),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    f"C{octave}",
                )

        # ── Paso 3: Teclas negras a la DERECHA (tocando piano roll) ─────────
        black_h = rh * 0.65
        black_w = w * 0.7
        black_x = w - black_w  # Posición X: pegadas al borde derecho

        for pitch in range(PIANO_LOWEST_PITCH, PIANO_HIGHEST_PITCH + 1):
            if not _is_black(pitch):
                continue

            idx = pitch - PIANO_LOWEST_PITCH
            y = idx * rh - self._scroll_offset
            rect = QRect(int(black_x), int(y), int(black_w), int(black_h))

            if pitch in self._active_colors:
                note_color = QColor(self._active_colors[pitch])
                note_color.setAlpha(200)
                grad = QLinearGradient(0, 0, 0, black_h)
                grad.setColorAt(0, note_color.lighter(150))
                grad.setColorAt(1, note_color)
                painter.fillRect(rect, grad)
                painter.setPen(QPen(note_color.darker(130), 1))
                painter.drawRect(rect)
            else:
                grad = QLinearGradient(0, 0, 0, black_h)
                grad.setColorAt(0, QColor(COLOR_KEY_BLACK))
                grad.setColorAt(1, QColor(COLOR_KEY_BLACK_BOTTOM))
                painter.fillRect(rect, grad)

        # ── Borde izquierdo (separa del sidebar) ─────────────────────────────
        painter.setPen(QPen(QColor(COLOR_KEY_BORDER), 2))
        painter.drawLine(0, 0, 0, h)

        painter.end()
