"""
piano_roll_view.py — QGraphicsView con notas cayendo, zoom y scroll.
"""

from typing import List, Optional

from PyQt6.QtCore import Qt, QRectF, pyqtSlot, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient,
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsLineItem,
)

from ui.styles import (
    PIANO_LOWEST_PITCH, PIANO_HIGHEST_PITCH, PIANO_NUM_KEYS,
    COLOR_ROLL_BG, COLOR_ROLL_GRID_LINE, COLOR_ROLL_PLAYHEAD,
    ROLL_NOTE_SPEED,
    PIANO_WIDGET_WIDTH,
)
from engine.midi_parser import NoteEvent


class PianoRollView(QGraphicsView):
    """
    Vista de piano roll con notas que caen de derecha a izquierda.
    Soporta zoom (25%-400%) y scroll vertical/horizontal.
    """

    seek_requested = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("piano_roll_view")

        # Escena
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Configuración visual
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setStyleSheet(f"""
            background-color: {COLOR_ROLL_BG};
            border: none;
        """)

        # Datos
        self._notes: List[NoteEvent] = []
        self._note_items: List[QGraphicsRectItem] = []
        self._grid_lines: List[QGraphicsLineItem] = []
        self._playhead: Optional[QGraphicsLineItem] = None

        # Tiempo
        self._current_time = 0.0
        self._duration = 0.0
        self._playhead_x = 0.0  # Posición fija: justo al lado del piano

        # Zoom
        self._zoom = 1.0  # 1.0 = 100%

        # Escala base (se recalcula al resize)
        self._base_row_height = 0.0
        self._base_pps = ROLL_NOTE_SPEED  # pixels per second base

        self._recalc_scale()
        self._draw_grid()
        self._draw_playhead()

    @property
    def _row_height(self):
        return self._base_row_height * self._zoom

    @property
    def _pixels_per_second(self):
        return self._base_pps * self._zoom

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._recalc_scale()
        self._rebuild_scene()

    def _recalc_scale(self):
        h = self.height()
        if h <= 0:
            h = 600
        self._base_row_height = h / PIANO_NUM_KEYS
        self._base_pps = max(100, self._base_row_height * 6)

    # ── Zoom ─────────────────────────────────────────────────────────────────

    def set_zoom(self, zoom: float):
        """Establece el factor de zoom (1.0 = 100%). Mínimo 100%."""
        self._zoom = max(1.0, min(zoom, 4.0))
        self._rebuild_scene()
        # Centrar verticalmente en el piano C4 al hacer zoom
        c4_idx = PIANO_NUM_KEYS - 1 - (60 - PIANO_LOWEST_PITCH)
        c4_y = c4_idx * self._row_height
        viewport_center = self.viewport().height() / 2
        self.verticalScrollBar().setValue(int(c4_y - viewport_center))

    # ── Rebuild completo ─────────────────────────────────────────────────────

    def _rebuild_scene(self):
        """Reconstruye toda la escena con la escala actual."""
        self._scene.clear()
        self._note_items.clear()
        self._grid_lines.clear()
        self._playhead = None

        if not self._notes:
            self._draw_empty_grid()
            return

        self._create_note_items()
        self._draw_grid()
        self._draw_playhead()
        self._update_playhead_position()

    def _draw_empty_grid(self):
        """Dibuja grid vacío cuando no hay notas."""
        w = max(self.width(), 2000)
        h = PIANO_NUM_KEYS * self._row_height
        for i in range(PIANO_NUM_KEYS + 1):
            y = i * self._row_height
            line = self._scene.addLine(0, y, w, y, QPen(QColor(COLOR_ROLL_GRID_LINE), 0.5))
            self._grid_lines.append(line)
        self._scene.setSceneRect(0, 0, w, h)

    # ── Carga de datos ───────────────────────────────────────────────────────

    def load_notes(self, notes: List[NoteEvent], duration: float):
        self._notes = notes
        self._duration = duration
        self._current_time = 0.0
        self._rebuild_scene()
        # Ajustar scroll al inicio
        self.verticalScrollBar().setValue(0)
        self.horizontalScrollBar().setValue(0)

    def clear_all(self):
        self._scene.clear()
        self._note_items.clear()
        self._grid_lines.clear()
        self._playhead = None

    # ── Crear items gráficos ─────────────────────────────────────────────────

    def _create_note_items(self):
        for note in self._notes:
            note_idx = note.pitch - PIANO_LOWEST_PITCH
            y = (PIANO_NUM_KEYS - 1 - note_idx) * self._row_height

            x = self._playhead_x + (note.start - self._current_time) * self._pixels_per_second
            width = note.duration * self._pixels_per_second
            height = self._row_height - 1

            rect = QRectF(x, y, width, height)
            item = QGraphicsRectItem(rect)

            color = QColor(note.color)
            color.setAlpha(220)

            grad = QLinearGradient(x, y, x, y + height)
            grad.setColorAt(0, color.lighter(120))
            grad.setColorAt(1, color)
            item.setBrush(QBrush(grad))

            border_color = color.darker(130)
            border_color.setAlpha(100)
            item.setPen(QPen(border_color, 0.5))

            opacity = 0.5 + (note.velocity / 127) * 0.5
            item.setOpacity(opacity)

            self._scene.addItem(item)
            self._note_items.append(item)

    # ── Grid ─────────────────────────────────────────────────────────────────

    def _draw_grid(self):
        w = max(
            self.width(),
            self._duration * self._pixels_per_second + self._playhead_x + 200
        )
        h = PIANO_NUM_KEYS * self._row_height

        for i in range(PIANO_NUM_KEYS + 1):
            y = i * self._row_height
            line = self._scene.addLine(0, y, w, y, QPen(QColor(COLOR_ROLL_GRID_LINE), 0.5))
            self._grid_lines.append(line)

        self._scene.setSceneRect(0, 0, w, h)

    # ── Playhead ─────────────────────────────────────────────────────────────

    def _draw_playhead(self):
        h = PIANO_NUM_KEYS * self._row_height
        pen = QPen(QColor(COLOR_ROLL_PLAYHEAD), 2.0)
        self._playhead = self._scene.addLine(
            self._playhead_x, 0, self._playhead_x, h, pen
        )
        self._playhead.setZValue(100)

    def _update_playhead_position(self):
        if self._playhead is None:
            return

        h = PIANO_NUM_KEYS * self._row_height
        self._playhead.setLine(self._playhead_x, 0, self._playhead_x, h)

        for i, note in enumerate(self._notes):
            if i < len(self._note_items):
                item = self._note_items[i]
                new_x = self._playhead_x + (note.start - self._current_time) * self._pixels_per_second
                width = note.duration * self._pixels_per_second
                rect = QRectF(new_x, item.rect().y(), width, item.rect().height())
                item.setRect(rect)

    # ── Slots ────────────────────────────────────────────────────────────────

    @pyqtSlot(float)
    def on_position_changed(self, position: float):
        self._current_time = position
        self._update_playhead_position()

    # ── Interacción ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            scene_pos = self.mapToScene(int(pos.x()), int(pos.y()))
            time_sec = (scene_pos.x() - self._playhead_x) / self._pixels_per_second
            time_sec = max(0.0, min(time_sec, self._duration))
            self.seek_requested.emit(time_sec)
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        """Scroll normal — sin zoom con rueda del mouse."""
        # Dejar que el QGraphicsView maneje el scroll por defecto
        super().wheelEvent(event)
