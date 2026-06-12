"""
transcription_worker.py — QThread que ejecuta basic-pitch predict() en background.
"""

import sys
import pathlib
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal


class TranscriptionWorker(QThread):
    """
    Ejecuta la transcripción de audio a MIDI en un thread separado
    para no bloquear la interfaz gráfica.
    """

    # Señales
    progress = pyqtSignal(int)          # 0-100
    finished = pyqtSignal(object, object)  # (PrettyMIDI, list[NoteEvent])
    error = pyqtSignal(str)             # mensaje de error
    status = pyqtSignal(str)            # mensaje de estado

    def __init__(self, audio_path: str, settings: dict, parent=None):
        super().__init__(parent)
        self.audio_path = audio_path
        self.settings = settings

    def run(self):
        try:
            audio_file = pathlib.Path(self.audio_path)
            if not audio_file.exists():
                self.error.emit(f"Archivo no encontrado: {self.audio_path}")
                return

            # Asegurar que basic_pitch esté en el path
            frontend_dir = pathlib.Path(__file__).resolve().parent.parent
            basic_pitch_dir = frontend_dir.parent / "basic-pitch"
            if str(basic_pitch_dir) not in sys.path:
                sys.path.insert(0, str(basic_pitch_dir))
            if str(frontend_dir) not in sys.path:
                sys.path.insert(0, str(frontend_dir))

            self.status.emit("Cargando modelo de transcripción...")
            self.progress.emit(5)

            # Importar basic-pitch
            try:
                import logging
                logging.getLogger().setLevel(logging.ERROR)
                from basic_pitch.inference import predict
            except ImportError as e:
                self.error.emit(
                    f"basic-pitch no se pudo importar:\n{str(e)}\n\n"
                    f"basic-pitch-main path: {basic_pitch_dir}\n"
                    f"¿Existe? {basic_pitch_dir.exists()}"
                )
                return

            self.progress.emit(15)
            self.status.emit("Analizando audio...")

            # Ejecutar predicción con parámetros del usuario
            onset_thresh = self.settings.get("onset_threshold", 0.5)
            frame_thresh = self.settings.get("frame_threshold", 0.3)
            min_note_len = self.settings.get("minimum_note_length", 127.0)
            min_freq = self.settings.get("minimum_frequency")
            max_freq = self.settings.get("maximum_frequency")

            model_output, midi_data, note_events = predict(
                str(audio_file),
                onset_threshold=onset_thresh,
                frame_threshold=frame_thresh,
                minimum_note_length=min_note_len,
                minimum_frequency=min_freq,
                maximum_frequency=max_freq,
            )

            self.progress.emit(80)
            self.status.emit("Parseando resultados...")

            # Convertir a eventos de nota
            from engine.midi_parser import parse_midi
            notes = parse_midi(midi_data)

            self.progress.emit(100)
            self.status.emit("Transcripción completada")

            self.finished.emit(midi_data, notes)

        except Exception as e:
            self.error.emit(f"Error durante la transcripción:\n{str(e)}")
