"""
app.py — MainWindow principal de alesito.mix: layout, señales y orquestación.
"""

import sys
import os
import pathlib

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QMessageBox, QApplication,
)

from ui.styles import QSS, SIDEBAR_WIDTH, PIANO_WIDGET_WIDTH
from ui.sidebar import Sidebar
from ui.piano_widget import PianoWidget
from ui.piano_roll_view import PianoRollView
from engine.playback_engine import PlaybackEngine
from transcription.transcription_worker import TranscriptionWorker
from engine.midi_parser import parse_midi, get_midi_info


class MainWindow(QMainWindow):
    """
    Ventana principal fullscreen.
    Layout: Sidebar | Piano Vertical | Piano Roll View
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("alesito.mix — Transcriptor de Audio a MIDI")
        self.setMinimumSize(1200, 700)

        # Estado
        self._current_audio_path = ""
        self._current_midi_data = None
        self._current_notes = []
        self._midi_save_path = ""

        # Motor de reproducción
        sf2_path = self._find_sf2()
        self._playback = PlaybackEngine(sf2_path, parent=self)

        # Worker de transcripción
        self._worker = None

        # Overlay de carga
        from ui.loading_overlay import LoadingOverlay
        self._overlay = LoadingOverlay(parent=self)
        self._overlay.cancel_clicked.connect(self._on_cancel_transcription)

        self._setup_ui()
        self._connect_signals()

    def _find_sf2(self) -> str:
        """Busca el SoundFont SF2 en el directorio assets."""
        base = pathlib.Path(__file__).resolve().parent.parent
        # Buscamos en _base_dir (que es frontend)
        sf2_paths = [
            base / "FluidR3_GM.sf2",
            base / "fluidr3_gm.sf2",
            base / "FluidR3.sf2",
        ]
        for p in sf2_paths:
            if p.exists():
                return str(p)
        # Fallback: cualquier .sf2 en frontend/
        assets = base
        if assets.exists():
            for f in assets.iterdir():
                if f.suffix.lower() == ".sf2":
                    return str(f)
        return ""

    def _setup_ui(self):
        """Configura el layout principal: Sidebar | Piano | PianoRoll."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────────────
        self._sidebar = Sidebar()
        main_layout.addWidget(self._sidebar)

        # ── Piano Vertical ───────────────────────────────────────────────────
        self._piano = PianoWidget()
        main_layout.addWidget(self._piano)

        # ── Piano Roll View ──────────────────────────────────────────────────
        self._piano_roll = PianoRollView()
        main_layout.addWidget(self._piano_roll, 1)  # stretch factor 1

    def _connect_signals(self):
        """Conecta todas las señales entre componentes."""
        # Sidebar → Acciones
        self._sidebar.upload_clicked.connect(self._on_upload)
        self._sidebar.midi_loaded.connect(self._on_midi_loaded)
        self._sidebar.download_clicked.connect(self._on_download)
        self._sidebar.play_clicked.connect(self._on_play)
        self._sidebar.stop_clicked.connect(self._on_stop)
        self._sidebar.speed_changed.connect(self._on_speed_changed)
        self._sidebar.zoom_changed.connect(self._piano_roll.set_zoom)
        self._sidebar.zoom_changed.connect(self._piano.set_zoom)
        self._sidebar.apply_clicked.connect(self._on_apply_settings)
        self._sidebar.cancel_clicked.connect(self._on_cancel_transcription)

        # Piano Roll → Seek
        self._piano_roll.seek_requested.connect(self._on_seek)

        # Scroll sincronizado: piano roll vertical scroll → piano
        self._piano_roll.verticalScrollBar().valueChanged.connect(
            self._piano.set_scroll_offset
        )

        # Playback → Visualización
        self._playback.position_changed.connect(self._piano_roll.on_position_changed)
        self._playback.note_on.connect(self._piano.on_note_on)
        self._playback.note_off.connect(self._piano.on_note_off)
        self._playback.playback_started.connect(self._on_playback_started)
        self._playback.playback_paused.connect(self._on_playback_paused)
        self._playback.playback_stopped.connect(self._on_playback_stopped)
        self._playback.playback_finished.connect(self._on_playback_finished)
        self._playback.error.connect(self._on_playback_error)

    # ── Slots: Upload / Transcripción ────────────────────────────────────────

    def _on_upload(self, file_path: str):
        """Inicia la transcripción del archivo de audio."""
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(
                self, "Transcripción en curso",
                "Ya hay una transcripción en progreso. Espera a que termine."
            )
            return

        self._current_audio_path = file_path
        self._sidebar.set_status("Iniciando transcripción...")
        self._sidebar.set_progress(0)
        self._sidebar.disable_download()
        self._sidebar.disable_apply()
        self._sidebar.enable_cancel()

        # Mostrar overlay de carga
        nombre = os.path.basename(file_path)
        self._overlay.mostrar(nombre)

        # Obtener ajustes de transcripción del panel
        settings = self._sidebar.get_transcription_settings()

        # Auto-ajustar si está activado
        if self._sidebar.auto_adjust_enabled:
            from transcription.audio_analyzer import analyze_audio
            auto_settings = analyze_audio(file_path)
            settings.update(auto_settings)
            # Actualizar la UI con los valores auto-ajustados
            self._sidebar._onset_slider["slider"].setValue(
                int(auto_settings["onset_threshold"] * 100))
            self._sidebar._frame_slider["slider"].setValue(
                int(auto_settings["frame_threshold"] * 100))
            self._sidebar._minlen_slider["slider"].setValue(
                int(auto_settings["minimum_note_length"]))
            self._sidebar._freq_min_spin.setValue(
                int(auto_settings["minimum_frequency"]))
            self._sidebar._freq_max_spin.setValue(
                int(auto_settings["maximum_frequency"]))
            self._sidebar.set_status("Auto-ajustado según el audio...")

        # Crear y lanzar worker con ajustes
        self._worker = TranscriptionWorker(file_path, settings, parent=self)
        self._worker.progress.connect(self._overlay.set_progreso)
        self._worker.status.connect(self._overlay.set_mensaje)
        self._worker.finished.connect(self._on_transcription_finished)
        self._worker.error.connect(self._on_transcription_error)
        self._worker.start()

    def _on_midi_loaded(self, midi_path: str):
        """Carga un archivo MIDI directamente sin transcribir."""
        try:
            import pretty_midi
            midi_data = pretty_midi.PrettyMIDI(midi_path)
            notes = parse_midi(midi_data)

            self._current_midi_data = midi_data
            self._current_notes = notes
            self._current_audio_path = ""  # No hay audio fuente

            # Cargar en el piano roll
            duration = midi_data.get_end_time()
            self._piano_roll.load_notes(notes, duration)

            # Cargar en el motor de reproducción
            self._playback.load(midi_data, notes)

            # Info
            info = get_midi_info(midi_data)
            self._sidebar.set_midi_info(info['num_notes'], info['duration'], info['tempo'])
            self._sidebar.enable_download(midi_path)
            self._sidebar.enable_apply()

        except Exception as e:
            QMessageBox.critical(self, "Error al cargar MIDI", f"No se pudo cargar el MIDI:\n{str(e)}")

    def _on_transcription_finished(self, midi_data, notes):
        """Callback cuando la transcripción termina exitosamente."""
        self._current_midi_data = midi_data
        self._current_notes = notes

        # Cargar en el piano roll
        duration = midi_data.get_end_time()
        self._piano_roll.load_notes(notes, duration)

        # Cargar en el motor de reproducción
        self._playback.load(midi_data, notes)

        # Habilitar descarga
        stem = pathlib.Path(self._current_audio_path).stem
        self._midi_save_path = str(
            pathlib.Path(self._current_audio_path).parent / f"{stem}_transcrito.mid"
        )
        self._sidebar.enable_download(self._midi_save_path)
        self._sidebar.enable_apply()

        # Info
        info = get_midi_info(midi_data)
        self._sidebar.set_midi_info(info['num_notes'], info['duration'], info['tempo'])

        # Cerrar overlay con delay
        self._overlay.set_progreso(100)
        self._overlay.set_mensaje("Audio cargado ✓")
        QTimer.singleShot(2000, self._overlay.ocultar)

    def _on_transcription_error(self, msg: str):
        """Callback si la transcripción falla."""
        self._overlay.ocultar()
        self._sidebar.enable_apply()
        QMessageBox.critical(self, "Error de Transcripción", msg)

    def _on_cancel_transcription(self):
        """Cancela la transcripción en curso."""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(3000)
            self._overlay.ocultar()
            self._sidebar.enable_apply()
            self._sidebar.disable_cancel()

    def _on_apply_settings(self, settings: dict):
        """Re-transcribe con los nuevos ajustes, manteniendo la posición."""
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(
                self, "Transcripción en curso",
                "Ya hay una transcripción en progreso. Espera a que termine."
            )
            return

        if not self._current_audio_path:
            return

        # Advertencia si los umbrales son muy bajos
        if settings['onset_threshold'] < 0.1 and settings['frame_threshold'] < 0.1:
            respuesta = QMessageBox.question(
                self, "Umbrales muy bajos",
                "Los umbrales están muy bajos. Esto puede tardar mucho "
                "y detectar notas falsas por ruido.\n\n¿Continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if respuesta == QMessageBox.StandardButton.No:
                return

        # Pausar reproducción si está sonando
        was_playing = self._playback.playing
        if was_playing:
            self._playback.pause()

        # Guardar posición actual
        self._saved_position = self._playback.current_time

        self._sidebar.set_status("Re-transcribiendo con nuevos ajustes...")
        self._sidebar.set_progress(0)
        self._sidebar.disable_apply()
        self._sidebar.disable_download()
        self._sidebar.enable_cancel()

        # Mostrar overlay
        nombre = os.path.basename(self._current_audio_path)
        self._overlay.mostrar(f"{nombre} (re-transcripción)")

        # Lanzar worker con los nuevos ajustes
        self._worker = TranscriptionWorker(
            self._current_audio_path, settings, parent=self
        )
        self._worker.progress.connect(self._overlay.set_progreso)
        self._worker.status.connect(self._overlay.set_mensaje)
        self._worker.finished.connect(self._on_apply_finished)
        self._worker.error.connect(self._on_transcription_error)
        self._worker.start()

    def _on_apply_finished(self, midi_data, notes):
        """Callback cuando la re-transcripción termina."""
        self._current_midi_data = midi_data
        self._current_notes = notes

        # Cargar en el piano roll
        duration = midi_data.get_end_time()
        self._piano_roll.load_notes(notes, duration)

        # Cargar en el motor de reproducción
        self._playback.load(midi_data, notes)

        # Restaurar posición guardada
        pos = getattr(self, '_saved_position', 0.0)
        if pos > 0 and pos < duration:
            self._playback.seek(pos)

        # Habilitar descarga
        stem = pathlib.Path(self._current_audio_path).stem
        self._midi_save_path = str(
            pathlib.Path(self._current_audio_path).parent / f"{stem}_transcrito.mid"
        )
        self._sidebar.enable_download(self._midi_save_path)
        self._sidebar.enable_apply()

        # Info
        info = get_midi_info(midi_data)
        self._sidebar.set_midi_info(info['num_notes'], info['duration'], info['tempo'])

        # Cerrar overlay con delay
        self._overlay.set_progreso(100)
        self._overlay.set_mensaje("Cambios aplicados ✓")
        QTimer.singleShot(2000, self._overlay.ocultar)

    # ── Slots: Playback ──────────────────────────────────────────────────────

    def _on_play(self):
        """Alterna play/pause."""
        if self._playback.playing:
            self._playback.pause()
        else:
            self._playback.play()

    def _on_stop(self):
        """Detiene la reproducción."""
        self._playback.stop()
        self._piano.clear_highlights()

    def _on_seek(self, time_sec: float):
        """Seek a una posición temporal."""
        self._playback.seek(time_sec)

    def _on_speed_changed(self, speed: float):
        """Cambia la velocidad de reproducción."""
        self._playback.set_speed(speed)

    def _on_playback_started(self):
        self._sidebar.set_playing_state(True)

    def _on_playback_paused(self):
        self._sidebar.set_playing_state(False)

    def _on_playback_stopped(self):
        self._sidebar.set_playing_state(False)
        self._piano.clear_highlights()

    def _on_playback_finished(self):
        self._sidebar.set_playing_state(False)
        self._piano.clear_highlights()
        self._sidebar.set_status("Reproducción completada")

    def _on_playback_error(self, msg: str):
        self._sidebar.set_status("Error de reproducción")
        QMessageBox.warning(self, "Error de Reproducción", msg)

    # ── Slots: Download ──────────────────────────────────────────────────────

    def _on_download(self, path: str):
        """Guarda el MIDI transcrito."""
        if self._current_midi_data is None:
            return
        try:
            self._current_midi_data.write(path)
            self._sidebar.set_status(f"MIDI guardado: {pathlib.Path(path).name}")
        except Exception as e:
            QMessageBox.critical(
                self, "Error al guardar",
                f"No se pudo guardar el MIDI:\n{str(e)}"
            )

    # ── Eventos de ventana ───────────────────────────────────────────────────

    def keyPressEvent(self, event):
        """Escape sale del fullscreen."""
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                QApplication.quit()
        # Espacio alterna play/pause
        elif event.key() == Qt.Key.Key_Space:
            self._on_play()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Limpia recursos al cerrar."""
        self._playback.stop()
        event.accept()
