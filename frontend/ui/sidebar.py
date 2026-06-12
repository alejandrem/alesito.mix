"""
sidebar.py — Widget de la sidebar: upload, download, play/stop, ajustes de transcripción.
"""

import os

from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QProgressBar, QFileDialog, QSlider,
    QFrame, QSpinBox, QSizePolicy, QScrollArea,
)

from ui.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_GOLD,
    COLOR_WOOD_BORDER, SIDEBAR_WIDTH,
)

from ui.help_tooltip import HelpTooltip


class NoScrollSlider(QSlider):
    """QSlider que ignora eventos de rueda del mouse (scroll)."""
    def wheelEvent(self, event):
        event.ignore()


class NoScrollSpinBox(QSpinBox):
    """QSpinBox que ignora eventos de rueda del mouse (scroll)."""
    def wheelEvent(self, event):
        event.ignore()


class Sidebar(QWidget):
    """
    Sidebar con controles de la app: subir archivo, descargar MIDI,
    play/pause/stop, barra de progreso, velocidad y ajustes de transcripción.
    """

    # Señales
    upload_clicked = pyqtSignal(str)
    midi_loaded = pyqtSignal(str)       # ruta del archivo MIDI cargado
    download_clicked = pyqtSignal(str)
    play_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    speed_changed = pyqtSignal(float)
    settings_changed = pyqtSignal(dict)
    zoom_changed = pyqtSignal(float)
    apply_clicked = pyqtSignal(dict)
    cancel_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()     # aplicar ajustes de transcripción

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(SIDEBAR_WIDTH)
        self.setMaximumWidth(SIDEBAR_WIDTH)

        self._midi_saved_path = ""
        self._setup_ui()

    def _setup_ui(self):
        # ── Scroll wrapper ───────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setObjectName("sidebar_scroll")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # ── Título ───────────────────────────────────────────────────────────
        title = QLabel("alesito.mix")
        title.setObjectName("sidebar_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("PIANO TRANSCRIBER")
        subtitle.setObjectName("sidebar_subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addWidget(self._separator())

        # ── Nombre del archivo ───────────────────────────────────────────────
        self._label_filename = QLabel("Ningún archivo cargado")
        self._label_filename.setObjectName("label_filename")
        self._label_filename.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_filename.setWordWrap(True)
        layout.addWidget(self._label_filename)

        # ── Subir / Descargar en la misma línea ─────────────────────────────
        file_btns = QHBoxLayout()
        file_btns.setSpacing(6)

        self._btn_upload = QPushButton("SUBIR")
        self._btn_upload.setObjectName("btn_upload")
        self._btn_upload.clicked.connect(self._on_upload)
        file_btns.addWidget(self._btn_upload)

        self._btn_download = QPushButton("DESCARGAR")
        self._btn_download.setObjectName("btn_download")
        self._btn_download.setEnabled(False)
        self._btn_download.clicked.connect(self._on_download)
        file_btns.addWidget(self._btn_download)

        layout.addLayout(file_btns)

        layout.addWidget(self._separator())

        # ── Info del MIDI: Notas / Tiempo / BPM ─────────────────────────────
        info_row = QHBoxLayout()
        info_row.setSpacing(4)

        self._info_notes = QLabel("0 notas")
        self._info_notes.setObjectName("label_info")
        self._info_notes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_row.addWidget(self._info_notes)

        self._info_duration = QLabel("0.0s")
        self._info_duration.setObjectName("label_info")
        self._info_duration.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_row.addWidget(self._info_duration)

        self._info_bpm = QLabel("0 BPM")
        self._info_bpm.setObjectName("label_info")
        self._info_bpm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_row.addWidget(self._info_bpm)

        layout.addLayout(info_row)

        # ── Controles de reproducción + Auto-ajustar ─────────────────────────
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_play = QPushButton("▶")
        self._btn_play.setObjectName("btn_play")
        self._btn_play.clicked.connect(self._on_play)
        controls_layout.addWidget(self._btn_play)

        self._btn_stop = QPushButton("■")
        self._btn_stop.setObjectName("btn_stop")
        self._btn_stop.clicked.connect(self._on_stop)
        controls_layout.addWidget(self._btn_stop)

        self._btn_auto = QPushButton("✓")
        self._btn_auto.setObjectName("btn_auto")
        self._btn_auto.setCheckable(True)
        self._btn_auto.setToolTip("Auto-ajustar parámetros según el audio")
        self._btn_auto.clicked.connect(self._on_auto_toggle)
        controls_layout.addWidget(self._btn_auto)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        layout.addWidget(self._separator())

        # ── Velocidad ────────────────────────────────────────────────────────
        speed_title = QLabel("VELOCIDAD")
        speed_title.setObjectName("label_speed")
        speed_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(speed_title)

        speed_row = QHBoxLayout()
        speed_row.setSpacing(8)
        self._speed_slider = NoScrollSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setMinimum(25)
        self._speed_slider.setMaximum(200)
        self._speed_slider.setValue(100)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_row.addWidget(self._speed_slider)

        self._label_speed_value = QLabel("1.0x")
        self._label_speed_value.setMinimumWidth(35)
        self._label_speed_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        speed_row.addWidget(self._label_speed_value)
        layout.addLayout(speed_row)

        layout.addWidget(self._separator())

        # ── Ajustes de Transcripción (fijos, siempre visibles) ──────────────
        settings_title = QLabel("AJUSTES DE TRANSCRIPCIÓN")
        settings_title.setObjectName("label_speed")
        settings_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(settings_title)

        # Tooltip de ayuda
        self._help_tooltip = HelpTooltip(parent=self)

        # Textos de ayuda
        self._help_texts = {
            "onset": (
                "Controla qué tan sensible es el sistema para detectar el golpe "
                "o ataque inicial de una nota.\n\n"
                "Valores bajos: Vuelven al modelo muy sensible. Si una nota larga "
                "tambalea un poco en volumen, la IA puede interpretarlo como nuevos "
                "golpes y dividirla en varias notas cortas.\n\n"
                "Valores altos: Hacen al modelo más estricto. Si tu audio tiene mucho "
                "eco, reverberación o ruido, subir este valor evita que esos reflejos "
                "generen notas falsas."
            ),
            "frame": (
                "Controla la confianza del modelo para mantener una nota encendida "
                "en el tiempo, evaluando el sonido cuadro por cuadro.\n\n"
                "Valores bajos: Reducen la exigencia de la IA, ideal si notas que "
                "las melodías se cortan antes de tiempo o suenan muy 'staccato'. "
                "Ayuda a que el sostén dure más.\n\n"
                "Valores altos: Son más estrictos con la energía del sonido. Hace "
                "que las notas se apaguen rápido en cuanto el volumen disminuye."
            ),
            "minlen": (
                "Define la duración mínima requerida en milisegundos para registrar "
                "una nota de manera válida.\n\n"
                "Valores bajos: Permiten capturar adornos rapidísimos, notas de paso "
                "o ejecuciones muy veloces.\n\n"
                "Valores altos: Actúa como un filtro de limpieza. Evita que pequeños "
                "ruidos transitorios o golpes de aire se conviertan en micro-notas "
                "indeseadas ('notas fantasma')."
            ),
            "freq": (
                "Delimita el rango de tonos permitidos en la transcripción para "
                "ignorar ruidos ajenos al instrumento.\n\n"
                "Frecuencia Mínima: Súbela si el audio tiene frecuencias graves "
                "molestas (pisadas, vibración, golpes al micrófono).\n\n"
                "Frecuencia Máxima: Bájala para bloquear siseos agudos, estática "
                "de fondo o ruidos que no correspondan a la música."
            ),
        }

        self._info_buttons = {}

        # Onset Threshold
        self._onset_slider = self._make_slider(
            "Umbral de Inicio", 0.0, 1.0, 0.5, 100
        )
        layout.addWidget(self._make_labeled_row(
            self._onset_slider["label"], "onset"
        ))
        layout.addLayout(self._onset_slider["row"])

        # Frame Threshold
        self._frame_slider = self._make_slider(
            "Umbral de Sostén", 0.0, 1.0, 0.3, 100
        )
        layout.addWidget(self._make_labeled_row(
            self._frame_slider["label"], "frame"
        ))
        layout.addLayout(self._frame_slider["row"])

        # Minimum Note Length
        self._minlen_slider = self._make_slider(
            "Largo Mínimo (ms)", 20, 500, 127, 1
        )
        layout.addWidget(self._make_labeled_row(
            self._minlen_slider["label"], "minlen"
        ))
        layout.addLayout(self._minlen_slider["row"])

        # Frecuencia Mínima y Máxima en la misma línea
        freq_label = QLabel("RANGO DE FRECUENCIAS")
        freq_label.setObjectName("label_settings")
        freq_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; font-weight: normal;")
        freq_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        freq_title = self._make_labeled_row(freq_label, "freq")
        layout.addWidget(freq_title)

        freq_row = QHBoxLayout()
        freq_row.setSpacing(8)

        freq_min_box = QVBoxLayout()
        freq_min_box.setSpacing(2)
        freq_min_label = QLabel("Mín")
        freq_min_label.setObjectName("label_settings")
        self._freq_min_spin = NoScrollSpinBox()
        self._freq_min_spin.setRange(20, 2000)
        self._freq_min_spin.setValue(65)
        self._freq_min_spin.setSuffix(" Hz")
        self._freq_min_spin.setFixedWidth(80)
        self._freq_min_spin.valueChanged.connect(self._on_settings_changed)
        freq_min_box.addWidget(freq_min_label)
        freq_min_box.addWidget(self._freq_min_spin)
        freq_row.addLayout(freq_min_box)

        freq_max_box = QVBoxLayout()
        freq_max_box.setSpacing(2)
        freq_max_label = QLabel("Máx")
        freq_max_label.setObjectName("label_settings")
        self._freq_max_spin = NoScrollSpinBox()
        self._freq_max_spin.setRange(500, 12000)
        self._freq_max_spin.setValue(6000)
        self._freq_max_spin.setSuffix(" Hz")
        self._freq_max_spin.setFixedWidth(80)
        self._freq_max_spin.valueChanged.connect(self._on_settings_changed)
        freq_max_box.addWidget(freq_max_label)
        freq_max_box.addWidget(self._freq_max_spin)
        freq_row.addLayout(freq_max_box)

        layout.addLayout(freq_row)

        # Nota informativa
        info = QLabel("Ajustar según instrumento y ruido del audio")
        info.setObjectName("label_status")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Botones Aplicar / Cancelar / Restablecer
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_apply = QPushButton("APLICAR")
        self._btn_apply.setObjectName("btn_apply")
        self._btn_apply.setEnabled(False)
        self._btn_apply.clicked.connect(self._on_apply)
        btn_row.addWidget(self._btn_apply)

        self._btn_cancel = QPushButton("CANCELAR")
        self._btn_cancel.setObjectName("btn_cancel")
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._btn_cancel)

        self._btn_reset = QPushButton("RESTABLECER")
        self._btn_reset.setObjectName("btn_reset")
        self._btn_reset.clicked.connect(self._on_reset)
        btn_row.addWidget(self._btn_reset)

        layout.addLayout(btn_row)

        layout.addWidget(self._separator())

        # ── Zoom ─────────────────────────────────────────────────────────────
        zoom_title = QLabel("ZOOM")
        zoom_title.setObjectName("label_speed")
        zoom_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(zoom_title)

        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(8)

        self._zoom_out_btn = QPushButton("−")
        self._zoom_out_btn.setObjectName("btn_zoom")
        self._zoom_out_btn.setFixedSize(24, 24)
        self._zoom_out_btn.clicked.connect(self._on_zoom_out)
        zoom_row.addWidget(self._zoom_out_btn)

        self._zoom_slider = NoScrollSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setMinimum(100)   # 100% mínimo
        self._zoom_slider.setMaximum(400)   # 400% máximo
        self._zoom_slider.setValue(100)      # 100% default
        self._zoom_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_row.addWidget(self._zoom_slider)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setObjectName("btn_zoom")
        self._zoom_in_btn.setFixedSize(24, 24)
        self._zoom_in_btn.clicked.connect(self._on_zoom_in)
        zoom_row.addWidget(self._zoom_in_btn)

        self._label_zoom_value = QLabel("100%")
        self._label_zoom_value.setMinimumWidth(40)
        self._label_zoom_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_row.addWidget(self._label_zoom_value)

        layout.addLayout(zoom_row)

        self._zoom_reset_btn = QPushButton("Restablecer zoom")
        self._zoom_reset_btn.setObjectName("btn_zoom_reset")
        self._zoom_reset_btn.clicked.connect(self._on_zoom_reset)
        layout.addWidget(self._zoom_reset_btn)

        layout.addWidget(self._separator())

        # ── Footer ───────────────────────────────────────────────────────────
        footer = QLabel("powered by basic-pitch")
        footer.setObjectName("label_status")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        # ── Montar scroll ────────────────────────────────────────────────────
        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _make_labeled_row(self, label: QLabel, help_key: str) -> QWidget:
        """Crea una fila con label + botón (i) diminuto."""
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)

        row.addWidget(label)

        info_btn = QPushButton("i")
        info_btn.setFixedSize(14, 14)
        info_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLOR_WOOD_BORDER};
                border: none;
                font-size: 9px;
                font-weight: bold;
                font-style: italic;
                padding: 0px;
            }}
            QPushButton:hover {{
                color: {COLOR_GOLD};
            }}
        """)
        info_btn.clicked.connect(lambda checked, k=help_key: self._show_help(k))
        self._info_buttons[help_key] = info_btn
        row.addWidget(info_btn)
        row.addStretch()

        return container

    def _show_help(self, key: str):
        """Muestra el tooltip de ayuda para la clave dada."""
        texto = self._help_texts.get(key, "")
        btn = self._info_buttons.get(key)
        if texto and btn:
            self._help_tooltip.mostrar(texto, btn)

    def _make_slider(self, name: str, min_val: float, max_val: float,
                     default: float, scale: int) -> dict:
        """
        Crea un slider estilo velocidad: etiqueta arriba, slider + valor abajo.
        Retorna dict con "label", "row", "slider", "value_label".
        """
        label = QLabel(name)
        label.setObjectName("label_settings")

        row = QHBoxLayout()
        row.setSpacing(8)

        slider = NoScrollSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(int(min_val * scale))
        slider.setMaximum(int(max_val * scale))
        slider.setTickPosition(QSlider.TickPosition.NoTicks)

        # Bloquear señales para que setValue no dispare _on_settings_changed
        # antes de que todos los sliders estén creados
        slider.blockSignals(True)
        slider.setValue(int(default * scale))
        slider.blockSignals(False)

        slider.valueChanged.connect(self._on_settings_changed)

        value_label = QLabel(f"{default:.2f}" if scale > 1 else f"{int(default)}")
        value_label.setMinimumWidth(35)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        row.addWidget(slider)
        row.addWidget(value_label)

        slider._scale = scale
        slider._value_label = value_label

        return {"label": label, "row": row, "slider": slider, "value_label": value_label}

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        return sep

    # ── Slots ────────────────────────────────────────────────────────────────

    def _on_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de audio o MIDI",
            "",
            "Audio/MIDI (*.mp3 *.wav *.flac *.ogg *.m4a *.mid *.midi);;Todos los archivos (*)"
        )
        if file_path:
            self._label_filename.setText(os.path.basename(file_path))
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ('.mid', '.midi'):
                self.midi_loaded.emit(file_path)
            else:
                self.upload_clicked.emit(file_path)

    def _on_download(self):
        if not self._midi_saved_path:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar MIDI", self._midi_saved_path,
            "MIDI (*.mid);;Todos los archivos (*)"
        )
        if file_path:
            self.download_clicked.emit(file_path)

    def _on_play(self):
        self.play_clicked.emit()

    def _on_stop(self):
        self.stop_clicked.emit()

    def _on_auto_toggle(self):
        checked = self._btn_auto.isChecked()
        if checked:
            self._btn_auto.setText("✓")
        else:
            self._btn_auto.setText("✓")

    @property
    def auto_adjust_enabled(self) -> bool:
        return self._btn_auto.isChecked()

    def _on_speed_changed(self, value: int):
        speed = value / 100.0
        self._label_speed_value.setText(f"{speed:.1f}x")
        self.speed_changed.emit(speed)

    def _on_settings_changed(self):
        settings = self.get_transcription_settings()
        for ref in [self._onset_slider, self._frame_slider, self._minlen_slider]:
            sl = ref["slider"]
            vl = ref["value_label"]
            val = sl.value() / sl._scale
            vl.setText(f"{val:.2f}" if sl._scale > 1 else f"{int(val)}")
        self.settings_changed.emit(settings)

    def _on_zoom_in(self):
        val = self._zoom_slider.value()
        self._zoom_slider.setValue(min(val + 10, 400))

    def _on_zoom_out(self):
        val = self._zoom_slider.value()
        self._zoom_slider.setValue(max(val - 10, 100))

    def _on_zoom_changed(self, value: int):
        zoom = value / 100.0
        self._label_zoom_value.setText(f"{value}%")
        self.zoom_changed.emit(zoom)

    def _on_zoom_reset(self):
        self._zoom_slider.setValue(100)

    def _on_apply(self):
        settings = self.get_transcription_settings()
        self.apply_clicked.emit(settings)

    def _on_cancel(self):
        self.cancel_clicked.emit()

    def _on_reset(self):
        # Restablecer sliders a valores por defecto
        self._onset_slider["slider"].setValue(50)    # 0.50
        self._frame_slider["slider"].setValue(30)    # 0.30
        self._minlen_slider["slider"].setValue(127)  # 127 ms
        self._freq_min_spin.setValue(65)              # 65 Hz
        self._freq_max_spin.setValue(6000)            # 6000 Hz
        self.reset_clicked.emit()

    # ── API pública ──────────────────────────────────────────────────────────

    def get_transcription_settings(self) -> dict:
        return {
            "onset_threshold": self._onset_slider["slider"].value()
                               / self._onset_slider["slider"]._scale,
            "frame_threshold": self._frame_slider["slider"].value()
                               / self._frame_slider["slider"]._scale,
            "minimum_note_length": self._minlen_slider["slider"].value()
                                   / self._minlen_slider["slider"]._scale,
            "minimum_frequency": float(self._freq_min_spin.value()),
            "maximum_frequency": float(self._freq_max_spin.value()),
        }

    def set_progress(self, value: int):
        pass  # Barra de progreso eliminada

    def set_status(self, text: str):
        pass  # Mensajes de estado eliminados

    def enable_download(self, midi_path: str):
        self._midi_saved_path = midi_path
        self._btn_download.setEnabled(True)

    def disable_download(self):
        self._midi_saved_path = ""
        self._btn_download.setEnabled(False)

    def set_playing_state(self, is_playing: bool):
        self._btn_play.setText("❚❚" if is_playing else "▶")

    def set_midi_info(self, num_notes: int, duration: float, bpm: float):
        """Actualiza las etiquetas de info del MIDI."""
        self._info_notes.setText(f"{num_notes} notas")
        self._info_duration.setText(f"{duration:.1f}s")
        self._info_bpm.setText(f"{int(bpm)} BPM")

    def enable_apply(self):
        self._btn_apply.setEnabled(True)
        self._btn_cancel.setEnabled(False)

    def disable_apply(self):
        self._btn_apply.setEnabled(False)
        self._btn_cancel.setEnabled(True)

    def enable_cancel(self):
        self._btn_cancel.setEnabled(True)

    def disable_cancel(self):
        self._btn_cancel.setEnabled(False)
