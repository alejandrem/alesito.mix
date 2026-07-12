"""
piano_roll_view.py — QGraphicsView con notas cayendo, zoom y scroll.
"""

from typing import List, Optional

from PyQt6.QtCore import Qt, QRectF, pyqtSlot, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath,
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsLineItem,
)

from ui.styles import (
    PIANO_LOWEST_PITCH, PIANO_HIGHEST_PITCH, PIANO_NUM_KEYS,
    COLOR_ROLL_BG, COLOR_ROLL_GRID_LINE, COLOR_ROLL_PLAYHEAD,
    ROLL_NOTE_SPEED,
    PIANO_WIDGET_WIDTH,
    pitch_to_color,
)
from engine.midi_parser import NoteEvent

NOTE_CORNER_RADIUS = 4
NOTE_GAP_PX = 6


class NoteItem(QGraphicsItem):
    """Item gráfico para notas con esquinas redondeadas."""

    def __init__(self, x, y, w, h, color: QColor, opacity: float, parent=None):
        super().__init__(parent)
        self._rect = QRectF(x, y, w, h)
        self._color = QColor(color)
        self._note_opacity = opacity
        border = QColor(color).darker(130)
        border.setAlpha(100)
        self._pen = QPen(border, 0.5)
        self._update_path()

    def _update_path(self):
        self._path = QPainterPath()
        self._path.addRoundedRect(self._rect, NOTE_CORNER_RADIUS, NOTE_CORNER_RADIUS)

    def boundingRect(self):
        return self._rect

    def shape(self):
        return self._path

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._note_opacity)

        grad = QLinearGradient(
            self._rect.x(), self._rect.y(),
            self._rect.x(), self._rect.y() + self._rect.height()
        )
        c = QColor(self._color)
        grad.setColorAt(0, c.lighter(120))
        grad.setColorAt(1, c)
        painter.setBrush(QBrush(grad))

        painter.setPen(self._pen)
        painter.drawPath(self._path)

    def pen(self):
        return self._pen

    def setPen(self, pen: QPen):
        self._pen = QPen(pen)
        self.update()

    def set_geometry(self, x, y, w, h):
        self.prepareGeometryChange()
        self._rect = QRectF(x, y, w, h)
        self._update_path()

    def set_color(self, color: QColor, keep_pen: bool = False):
        self._color = QColor(color)
        if not keep_pen:
            border = QColor(color).darker(130)
            border.setAlpha(100)
            self._pen = QPen(border, 0.5)
        self.update()

    def set_note_opacity(self, opacity: float):
        self._note_opacity = opacity
        self.update()


class PianoRollView(QGraphicsView):
    """
    Vista de piano roll con notas que caen de derecha a izquierda.
    Soporta zoom (25%-400%) y scroll vertical/horizontal.
    """

    seek_requested = pyqtSignal(float)
    note_deleted = pyqtSignal(object)  # Emite el NoteEvent eliminado
    note_right_clicked = pyqtSignal(object, object)  # (NoteEvent, QPoint global_pos)
    note_moved = pyqtSignal(object, str, float)  # (NoteEvent, direction, amount)

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
        self._note_items: List[NoteItem] = []
        self._grid_lines: List[QGraphicsLineItem] = []
        self._playhead: Optional[QGraphicsLineItem] = None
        self._selected_item: Optional[NoteItem] = None
        self._selected_note_original_pen: Optional[QPen] = None

        # Hacer que el view pueda recibir eventos de teclado
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Tiempo
        self._current_time = 0.0
        self._duration = 0.0
        self._playhead_x = 0.0  # Posición fija: justo al lado del piano

        # Zoom
        self._zoom = 1.0  # 1.0 = 100%

        # Escala base (se recalcula al resize)
        self._base_row_height = 0.0
        self._base_pps = ROLL_NOTE_SPEED  # pixels per second base

        # Precomputación de notas adyacentes (para gap entre notas)
        self._prev_note_of: dict[int, NoteEvent] = {}  # id(note) → nota anterior del mismo pitch

        self._recalc_scale()
        self._draw_grid()
        self._draw_playhead()

    @property
    def _row_height(self):
        return self._base_row_height * self._zoom

    @property
    def _pixels_per_second(self):
        return self._base_pps * self._zoom

    # ── Helpers de geometría ───────────────────────────────────────────────

    def _note_rect_with_gap(self, note: NoteEvent) -> tuple[float, float, float, float]:
        """Retorna (x, y, width, height) aplicando gap entre notas consecutivas del mismo pitch."""
        note_idx = note.pitch - PIANO_LOWEST_PITCH
        y = note_idx * self._row_height
        x = self._playhead_x + (note.start - self._current_time) * self._pixels_per_second
        width = note.duration * self._pixels_per_second
        height = self._row_height - 1

        # Lookup O(1): nota anterior del mismo pitch (precomputada)
        prev = self._prev_note_of.get(id(note))
        if prev is not None:
            gap_sec = note.start - prev.end
            if gap_sec >= 0:
                gap_px = gap_sec * self._pixels_per_second
                if gap_px < NOTE_GAP_PX:
                    reduction = min(NOTE_GAP_PX - gap_px, width * 0.4)
                    x += reduction / 2
                    width -= reduction
        return x, y, max(width, 1), height

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
        c4_idx = 60 - PIANO_LOWEST_PITCH
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
        self._selected_item = None
        self._selected_note_original_pen = None

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
            
            # Determinar si es línea de octava (entre Si y Do)
            # Ahora: graves arriba (fila 0 = A0, pitch 21)
            # Fila i tiene pitch: PIANO_LOWEST_PITCH + i
            is_octave_line = False
            if i > 0 and i < PIANO_NUM_KEYS:
                higher_pitch = PIANO_LOWEST_PITCH + i
                if higher_pitch % 12 == 0:  # Si la nota de abajo (mayor pitch) es un Do (C)
                    is_octave_line = True
            
            if is_octave_line:
                pen = QPen(QColor("#3C3C3C"), 1.5)
            else:
                pen = QPen(QColor(COLOR_ROLL_GRID_LINE), 0.5)
                
            line = self._scene.addLine(0, y, w, y, pen)
            self._grid_lines.append(line)
        self._scene.setSceneRect(0, 0, w, h)

    # ── Carga de datos ───────────────────────────────────────────────────────

    def _precompute_adjacency(self):
        """Precomputa qué nota es la inmediatamente anterior de cada nota, por pitch."""
        self._prev_note_of.clear()
        by_pitch: dict[int, list[NoteEvent]] = {}
        for n in self._notes:
            by_pitch.setdefault(n.pitch, []).append(n)
        for notes in by_pitch.values():
            notes.sort(key=lambda n: n.start)
            for i in range(1, len(notes)):
                self._prev_note_of[id(notes[i])] = notes[i - 1]

    def load_notes(self, notes: List[NoteEvent], duration: float):
        self._notes = notes
        self._duration = duration
        self._current_time = 0.0
        self._precompute_adjacency()
        self._rebuild_scene()
        # Ajustar scroll al inicio
        self.verticalScrollBar().setValue(0)
        self.horizontalScrollBar().setValue(0)

    def clear_all(self):
        self._scene.clear()
        self._note_items.clear()
        self._grid_lines.clear()
        self._playhead = None
        self._selected_item = None
        self._selected_note_original_pen = None

    def update_note_item(self, note: NoteEvent, keep_pen: bool = False):
        """Actualiza la posición visual de una nota después de un cambio."""
        if note not in self._notes:
            return
        idx = self._notes.index(note)
        if idx >= len(self._note_items):
            return

        self._precompute_adjacency()

        item = self._note_items[idx]
        x, y, width, height = self._note_rect_with_gap(note)

        item.set_geometry(x, y, width, height)
        item.set_color(QColor(note.color), keep_pen=keep_pen)
        item.set_note_opacity(0.5 + (note.velocity / 127) * 0.5)

    # ── Crear items gráficos ─────────────────────────────────────────────────

    def _create_note_items(self):
        for note in self._notes:
            x, y, width, height = self._note_rect_with_gap(note)

            color = QColor(note.color)
            opacity = 0.5 + (note.velocity / 127) * 0.5
            item = NoteItem(x, y, width, height, color, opacity)

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
            
            # Determinar si es línea de octava (entre Si y Do)
            is_octave_line = False
            if i > 0 and i < PIANO_NUM_KEYS:
                higher_pitch = PIANO_LOWEST_PITCH + i
                if higher_pitch % 12 == 0:
                    is_octave_line = True
                    
            if is_octave_line:
                pen = QPen(QColor("#3C3C3C"), 1.5)
            else:
                pen = QPen(QColor(COLOR_ROLL_GRID_LINE), 0.5)
                
            line = self._scene.addLine(0, y, w, y, pen)
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
                x, y, width, height = self._note_rect_with_gap(note)
                item.set_geometry(x, y, width, height)

    # ── Slots ────────────────────────────────────────────────────────────────

    @pyqtSlot(float)
    def on_position_changed(self, position: float):
        self._current_time = position
        self._update_playhead_position()

    # ── Interacción ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        
        # Deseleccionar nota anterior si existe
        if self._selected_item and self._selected_note_original_pen:
            self._selected_item.setPen(self._selected_note_original_pen)
            self._selected_item = None
            self._selected_note_original_pen = None

        if isinstance(item, NoteItem) and item in self._note_items:
            # Seleccionar nueva nota
            self._selected_item = item
            self._selected_note_original_pen = item.pen()
            item.setPen(QPen(QColor("white"), 2.0))
            
            # Ola 4: Clic derecho para mostrar panel
            if event.button() == Qt.MouseButton.RightButton:
                idx = self._note_items.index(item)
                note = self._notes[idx]
                global_pos = event.globalPosition().toPoint()
                self.note_right_clicked.emit(note, global_pos)
            
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self._selected_item and self._selected_item in self._note_items:
                idx = self._note_items.index(self._selected_item)
                note = self._notes[idx]

                # Remover de las listas
                self._notes.remove(note)
                self._scene.removeItem(self._selected_item)
                self._note_items.remove(self._selected_item)

                self._selected_item = None
                self._selected_note_original_pen = None

                # Avisar al resto del programa
                self.note_deleted.emit(note)

        elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down,
                             Qt.Key.Key_Left, Qt.Key.Key_Right):
            # Mover nota con flechas (Ola 5)
            if self._selected_item and self._selected_item in self._note_items:
                idx = self._note_items.index(self._selected_item)
                note = self._notes[idx]
                direction = event.key()

                if direction == Qt.Key.Key_Up:
                    # Subir pitch 1 semitono
                    if note.pitch < PIANO_HIGHEST_PITCH:
                        note.pitch += 1
                        note.color = pitch_to_color(note.pitch)
                        self.update_note_item(note, keep_pen=True)
                        self.note_moved.emit(note, "pitch", note.pitch)
                elif direction == Qt.Key.Key_Down:
                    # Bajar pitch 1 semitono
                    if note.pitch > PIANO_LOWEST_PITCH:
                        note.pitch -= 1
                        note.color = pitch_to_color(note.pitch)
                        self.update_note_item(note, keep_pen=True)
                        self.note_moved.emit(note, "pitch", note.pitch)
                elif direction == Qt.Key.Key_Right:
                    # Mover adelante 0.05 segundos
                    note.start += 0.05
                    note.end += 0.05
                    self.update_note_item(note, keep_pen=True)
                    self.note_moved.emit(note, "time", 0.05)
                elif direction == Qt.Key.Key_Left:
                    # Mover atrás 0.05 segundos
                    if note.start >= 0.05:
                        note.start -= 0.05
                        note.end -= 0.05
                        self.update_note_item(note, keep_pen=True)
                        self.note_moved.emit(note, "time", -0.05)
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        """Scroll normal — sin zoom con rueda del mouse."""
        # Dejar que el QGraphicsView maneje el scroll por defecto
        super().wheelEvent(event)
