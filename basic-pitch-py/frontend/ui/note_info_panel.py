"""
note_info_panel.py — Panel flotante de información y edición de nota (Ola 4 + Ola 5)
"""

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QFrame, QGridLayout, QWidget, QSpacerItem, QSizePolicy
)

from ui.styles import (
    COLOR_WOOD_DARK, COLOR_WOOD_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_GOLD, COLOR_WOOD_BORDER, COLOR_BG_DARK, COLOR_WOOD_MEDIUM,
    COLOR_GOLD_DIM, COLOR_GOLD_BRIGHT, NOTE_NAMES
)

# Rangos de velocity por dinámica
DYNAMICS_RANGES = {
    "ppp": (1, 16),
    "pp": (17, 33),
    "p": (34, 49),
    "mp": (50, 64),
    "mf": (65, 80),
    "f": (81, 96),
    "ff": (97, 112),
    "fff": (113, 127),
}

# Valor central de velocity para cada dinámica
DYNAMICS_CENTER = {
    "ppp": 8,
    "pp": 25,
    "p": 42,
    "mp": 57,
    "mf": 73,
    "f": 89,
    "ff": 105,
    "fff": 120,
}

# Figuras musicales: nombre -> factor relativo a la negra
FIGURE_FACTORS = {
    "Redonda": 4.0,
    "Blanca": 2.0,
    "Negra": 1.0,
    "Corchea": 0.5,
    "Semicorchea": 0.25,
    "Fusa": 0.125,
}


def velocity_to_dynamic(velocity: int) -> str:
    """Convierte un velocity MIDI a su dinámica aproximada."""
    if velocity <= 16: return "ppp"
    elif velocity <= 33: return "pp"
    elif velocity <= 49: return "p"
    elif velocity <= 64: return "mp"
    elif velocity <= 80: return "mf"
    elif velocity <= 96: return "f"
    elif velocity <= 112: return "ff"
    else: return "fff"


def duration_to_figure(duration: float, bpm: float) -> str:
    """Determina la figura musical más cercana dado un BPM."""
    if bpm <= 0:
        return "Negra"
    beat_duration = 60.0 / bpm
    ratio = duration / beat_duration

    figures = [
        ("Redonda", 4.0),
        ("Blanca", 2.0),
        ("Negra", 1.0),
        ("Corchea", 0.5),
        ("Semicorchea", 0.25),
        ("Fusa", 0.125),
    ]
    best_name = "Negra"
    best_diff = float("inf")
    for name, factor in figures:
        diff = abs(ratio - factor)
        if diff < best_diff:
            best_diff = diff
            best_name = name
    return best_name


class NoteInfoPanel(QDialog):
    pause_requested = pyqtSignal()
    # Señales para cambios en tiempo real (Ola 5)
    note_changed = pyqtSignal(object, dict)  # (NoteEvent, cambios_dict)
    note_change_committed = pyqtSignal(object, dict, bool)  # (NoteEvent, cambios, apply_to_sisters)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Ventana independiente sin bordes del SO, pero siempre encima
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        # Dimensiones para que se vea minimalista pero amplio
        self.setMinimumWidth(320)
        self.setMinimumHeight(500)

        # Para poder mover la ventana manualmente
        self._drag_pos = QPoint()

        # Estado de la nota actual (Ola 5)
        self._current_note = None
        self._original_state = None  # Snapshot al abrir
        self._bpm = 120.0

        # Fondo cafesito sólido y elegante (no transparente)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLOR_WOOD_DARK};
                border: 1px solid {COLOR_GOLD_DIM};
                border-radius: 6px;
            }}
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                font-family: "Inter", sans-serif;
                font-size: 13px;
            }}
            .title {{
                color: {COLOR_GOLD};
                font-family: "Playfair Display", serif;
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            .section-title {{
                color: {COLOR_TEXT_SECONDARY};
                font-size: 11px;
                font-weight: bold;
                margin-top: 5px;
                margin-bottom: 5px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            QComboBox {{
                background-color: {COLOR_BG_DARK};
                border: 1px solid {COLOR_WOOD_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                color: {COLOR_TEXT_PRIMARY};
                min-width: 100px;
                min-height: 20px;
            }}
            QComboBox:hover {{
                border-color: {COLOR_GOLD_DIM};
            }}
            QComboBox:disabled {{
                background-color: {COLOR_WOOD_DARK};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_WOOD_BORDER};
            }}
            QRadioButton {{
                color: {COLOR_TEXT_PRIMARY};
                spacing: 8px;
            }}
            QRadioButton:disabled {{
                color: {COLOR_TEXT_SECONDARY};
            }}
            QRadioButton::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 7px;
                border: 1px solid {COLOR_GOLD_DIM};
                background: {COLOR_BG_DARK};
            }}
            QRadioButton::indicator:checked {{
                background: {COLOR_GOLD};
            }}
            QRadioButton::indicator:disabled {{
                border: 1px solid {COLOR_WOOD_BORDER};
                background: {COLOR_WOOD_DARK};
            }}
            QPushButton {{
                background-color: {COLOR_WOOD_MEDIUM};
                border: 1px solid {COLOR_GOLD_DIM};
                border-radius: 4px;
                padding: 8px 16px;
                color: {COLOR_TEXT_PRIMARY};
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: {COLOR_GOLD};
                background-color: #4A3525;
            }}
            QPushButton:disabled {{
                background-color: {COLOR_BG_DARK};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_WOOD_BORDER};
            }}
            QFrame#h_line {{
                background-color: {COLOR_WOOD_BORDER};
                max-height: 1px;
                margin: 10px 0px;
            }}
        """)

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # -- Cabecera (Draggable zone visual) --
        header_layout = QHBoxLayout()
        title = QLabel("🎵 Editar Nota")
        title.setProperty("class", "title")
        header_layout.addWidget(title)

        # Botón sutil de cerrar en la esquina
        self.btn_x = QPushButton("✕")
        self.btn_x.setFixedSize(24, 24)
        self.btn_x.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLOR_TEXT_SECONDARY};
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                color: #A04040;
                background: transparent;
                border: none;
            }}
        """)
        self.btn_x.clicked.connect(self._on_cancel)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_x)

        main_layout.addLayout(header_layout)

        line1 = QFrame()
        line1.setObjectName("h_line")
        main_layout.addWidget(line1)

        # -- Info Grid (solo lectura) --
        info_grid = QGridLayout()
        info_grid.setSpacing(12)

        self.lbl_note = QLabel("-")
        self.lbl_octave = QLabel("-")
        self.lbl_start = QLabel("-")
        self.lbl_end = QLabel("-")
        self.lbl_duration = QLabel("-")
        self.lbl_dynamic = QLabel("-")

        # Resaltar los valores un poco más que las etiquetas
        for lbl in [self.lbl_note, self.lbl_octave, self.lbl_start, self.lbl_end, self.lbl_duration, self.lbl_dynamic]:
            lbl.setStyleSheet(f"color: {COLOR_GOLD}; font-weight: 500;")

        labels = [
            ("Nota:", self.lbl_note),
            ("Octava:", self.lbl_octave),
            ("Inicio:", self.lbl_start),
            ("Fin:", self.lbl_end),
            ("Duración:", self.lbl_duration),
            ("Dinámica:", self.lbl_dynamic)
        ]

        for row, (text, widget) in enumerate(labels):
            lbl_key = QLabel(text)
            lbl_key.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
            info_grid.addWidget(lbl_key, row, 0)
            info_grid.addWidget(widget, row, 1)

        main_layout.addLayout(info_grid)

        # ── Sección de edición (Ola 5) ──
        line2 = QFrame()
        line2.setObjectName("h_line")
        main_layout.addWidget(line2)

        edit_title = QLabel("MODO EDICIÓN")
        edit_title.setProperty("class", "section-title")
        main_layout.addWidget(edit_title)

        edit_layout = QGridLayout()
        edit_layout.setSpacing(12)

        # Dinámica
        lbl_dyn = QLabel("Dinámica:")
        lbl_dyn.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        self.combo_dynamic = QComboBox()
        self.combo_dynamic.addItems(list(DYNAMICS_RANGES.keys()))
        self.combo_dynamic.currentTextChanged.connect(self._on_dynamic_changed)
        edit_layout.addWidget(lbl_dyn, 0, 0)
        edit_layout.addWidget(self.combo_dynamic, 0, 1)

        # Figura
        lbl_fig = QLabel("Figura:")
        lbl_fig.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        self.combo_figure = QComboBox()
        self.combo_figure.addItems(list(FIGURE_FACTORS.keys()))
        self.combo_figure.currentTextChanged.connect(self._on_figure_changed)
        edit_layout.addWidget(lbl_fig, 1, 0)
        edit_layout.addWidget(self.combo_figure, 1, 1)

        # Nota destino (pitch)
        lbl_move = QLabel("Mover a:")
        lbl_move.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        move_layout = QHBoxLayout()

        self.combo_note = QComboBox()
        self.combo_note.addItems(NOTE_NAMES)
        self.combo_note.currentTextChanged.connect(self._on_note_changed)
        move_layout.addWidget(self.combo_note)

        self.combo_octave = QComboBox()
        self.combo_octave.addItems([str(i) for i in range(9)])
        self.combo_octave.currentTextChanged.connect(self._on_octave_changed)
        move_layout.addWidget(self.combo_octave)

        edit_layout.addLayout(move_layout, 2, 1)
        edit_layout.addWidget(lbl_move, 2, 0)

        main_layout.addLayout(edit_layout)

        # Hermanas
        main_layout.addSpacing(10)

        sister_label = QLabel("Aplicar cambios a:")
        sister_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        main_layout.addWidget(sister_label)

        self.radio_group = QButtonGroup(self)
        self.radio_single = QRadioButton("Solo esta nota")
        self.radio_all = QRadioButton("Todas las hermanas (mismo pitch)")
        self.radio_single.setChecked(True)
        self.radio_group.addButton(self.radio_single)
        self.radio_group.addButton(self.radio_all)

        main_layout.addWidget(self.radio_single)
        main_layout.addWidget(self.radio_all)

        main_layout.addStretch()

        # Botones inferiores
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("CANCELAR")
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {COLOR_WOOD_BORDER};
                color: {COLOR_TEXT_SECONDARY};
            }}
            QPushButton:hover {{
                border-color: {COLOR_TEXT_PRIMARY};
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        self.btn_cancel.clicked.connect(self._on_cancel)

        self.btn_save = QPushButton("GUARDAR CAMBIOS")
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_WOOD_MEDIUM};
                border: 1px solid {COLOR_GOLD};
                color: {COLOR_GOLD};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_WOOD_LIGHT};
                border-color: {COLOR_GOLD_BRIGHT};
            }}
        """)
        self.btn_save.clicked.connect(self._on_save)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)

        main_layout.addLayout(btn_layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.pause_requested.emit()

    def set_bpm(self, bpm: float):
        """Establece el BPM actual para cálculos de figura musical."""
        self._bpm = bpm if bpm > 0 else 120.0

    def update_info(self, note):
        """Actualiza la información mostrada del panel."""
        from ui.styles import pitch_to_name, pitch_to_octave

        self._current_note = note

        # Guardar estado original para poder revertir
        self._original_state = {
            "pitch": note.pitch,
            "start": note.start,
            "end": note.end,
            "velocity": note.velocity,
        }

        # Info básica
        self.lbl_note.setText(f"{pitch_to_name(note.pitch)}  (Pitch: {note.pitch})")
        self.lbl_octave.setText(str(pitch_to_octave(note.pitch)))
        self.lbl_start.setText(f"{note.start:.3f} s")
        self.lbl_end.setText(f"{note.end:.3f} s")
        self.lbl_duration.setText(f"{note.duration:.3f} s")

        # Determinar dinámica
        dyn = velocity_to_dynamic(note.velocity)
        self.lbl_dynamic.setText(f"{dyn.upper()}  (Velocidad: {note.velocity})")

        # Pre-seleccionar combobox de dinámica
        self.combo_dynamic.blockSignals(True)
        index = self.combo_dynamic.findText(dyn)
        if index >= 0:
            self.combo_dynamic.setCurrentIndex(index)
        self.combo_dynamic.blockSignals(False)

        # Pre-seleccionar combobox de figura
        fig = duration_to_figure(note.duration, self._bpm)
        self.combo_figure.blockSignals(True)
        index = self.combo_figure.findText(fig)
        if index >= 0:
            self.combo_figure.setCurrentIndex(index)
        self.combo_figure.blockSignals(False)

        # Pre-seleccionar combobox de pitch
        note_name = NOTE_NAMES[note.pitch % 12]
        octave = pitch_to_octave(note.pitch)
        self.combo_note.blockSignals(True)
        index = self.combo_note.findText(note_name)
        if index >= 0:
            self.combo_note.setCurrentIndex(index)
        self.combo_note.blockSignals(False)

        self.combo_octave.blockSignals(True)
        index = self.combo_octave.findText(str(octave))
        if index >= 0:
            self.combo_octave.setCurrentIndex(index)
        self.combo_octave.blockSignals(False)

        # Resetear radio button
        self.radio_single.setChecked(True)

    def _on_dynamic_changed(self, text: str):
        """Cuando cambia la selección de dinámica."""
        if not self._current_note:
            return
        new_velocity = DYNAMICS_CENTER.get(text, 72)
        self._current_note.velocity = new_velocity

        # Actualizar label
        self.lbl_dynamic.setText(f"{text.upper()}  (Velocidad: {new_velocity})")

        # Emitir cambio en tiempo real
        self.note_changed.emit(self._current_note, {"velocity": new_velocity})

    def _on_figure_changed(self, text: str):
        """Cuando cambia la selección de figura musical."""
        if not self._current_note:
            return
        factor = FIGURE_FACTORS.get(text, 1.0)
        beat_duration = 60.0 / self._bpm
        new_duration = beat_duration * factor
        new_end = self._current_note.start + new_duration

        self._current_note.end = new_end

        # Actualizar labels
        self.lbl_end.setText(f"{new_end:.3f} s")
        self.lbl_duration.setText(f"{new_duration:.3f} s")

        # Emitir cambio en tiempo real
        self.note_changed.emit(self._current_note, {"end": new_end, "old_start": self._current_note.start})

    def _on_note_changed(self, text: str):
        """Cuando cambia la nota (C, C#, etc.)."""
        self._update_pitch_from_combos()

    def _on_octave_changed(self, text: str):
        """Cuando cambia la octava."""
        self._update_pitch_from_combos()

    def _update_pitch_from_combos(self):
        """Calcula el nuevo pitch desde los combobox de nota y octava."""
        if not self._current_note:
            return

        note_name = self.combo_note.currentText()
        octave_str = self.combo_octave.currentText()

        if not note_name or not octave_str:
            return

        try:
            octave = int(octave_str)
        except ValueError:
            return

        # Calcular nuevo pitch
        note_index = NOTE_NAMES.index(note_name) if note_name in NOTE_NAMES else 0
        new_pitch = (octave + 1) * 12 + note_index

        # Limitar al rango del piano
        new_pitch = max(21, min(108, new_pitch))

        if new_pitch == self._current_note.pitch:
            return

        old_pitch = self._current_note.pitch
        self._current_note.pitch = new_pitch

        # Actualizar label
        from ui.styles import pitch_to_name, pitch_to_octave, pitch_to_color
        self.lbl_note.setText(f"{pitch_to_name(new_pitch)}  (Pitch: {new_pitch})")
        self.lbl_octave.setText(str(pitch_to_octave(new_pitch)))

        # Actualizar color de la nota
        self._current_note.color = pitch_to_color(new_pitch)

        # Emitir cambio en tiempo real
        self.note_changed.emit(self._current_note, {"pitch": new_pitch, "old_pitch": old_pitch, "old_start": self._current_note.start})

    def _on_cancel(self):
        """Revierte los cambios y cierra el panel."""
        if self._current_note and self._original_state:
            # Restaurar estado original
            self._current_note.pitch = self._original_state["pitch"]
            self._current_note.start = self._original_state["start"]
            self._current_note.end = self._original_state["end"]
            self._current_note.velocity = self._original_state["velocity"]

            from ui.styles import pitch_to_color
            self._current_note.color = pitch_to_color(self._current_note.pitch)

            # Emitir cambio para revertir visualización
            self.note_changed.emit(self._current_note, {
                "pitch": self._original_state["pitch"],
                "start": self._original_state["start"],
                "end": self._original_state["end"],
                "velocity": self._original_state["velocity"],
            })

        self.hide()

    def _on_save(self):
        """Confirma y aplica los cambios definitivamente."""
        if not self._current_note:
            return

        apply_to_sisters = self.radio_all.isChecked()

        # Recopilar todos los cambios realizados
        changes = {}
        if self._original_state:
            if self._current_note.pitch != self._original_state["pitch"]:
                changes["pitch"] = self._current_note.pitch
                changes["old_pitch"] = self._original_state["pitch"]
            if self._current_note.velocity != self._original_state["velocity"]:
                changes["velocity"] = self._current_note.velocity
            if abs(self._current_note.end - self._original_state["end"]) > 0.001:
                changes["end"] = self._current_note.end

        if changes:
            self.note_change_committed.emit(self._current_note, changes, apply_to_sisters)

        self._original_state = None
        self._current_note = None
        self.hide()

    # --- Lógica para arrastrar (mover) la ventana frameless ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
