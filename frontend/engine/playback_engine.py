"""
playback_engine.py — Motor de reproducción MIDI con FluidSynth y SoundFont SF2.
"""

import time
import pathlib
import sys
import os
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

import pretty_midi

from engine.midi_parser import NoteEvent


class PlaybackEngine(QObject):
    """
    Reproduce eventos MIDI usando FluidSynth con un SoundFont de piano de cola.
    Emite señales para sincronizar la visualización del piano roll y las teclas.
    """

    # Señales
    position_changed = pyqtSignal(float)   # posición actual en segundos
    note_on = pyqtSignal(int, int, str)   # (pitch, velocity, color_hex)
    note_off = pyqtSignal(int)             # (pitch)
    playback_started = pyqtSignal()
    playback_paused = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, sf2_path: str, parent=None):
        super().__init__(parent)
        self.sf2_path = sf2_path
        self.fs = None          # fluidsynth.Synth
        self.midi_data: Optional[pretty_midi.PrettyMIDI] = None
        self.notes: List[NoteEvent] = []
        self.playing = False
        self.paused = False
        self.current_time = 0.0
        self.start_real_time = 0.0
        self.speed = 1.0
        self.duration = 0.0
        self.volume_gain = 1.0  # Multiplicador de volumen (0.0 – 2.0)

        # Índice del próximo evento a procesar
        self._next_note_idx = 0
        self._active_notes: dict[int, float] = {}  # pitch -> scheduled_off_time

        # Timer para actualización de posición
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 FPS
        self._timer.timeout.connect(self._on_tick)

    def _init_fluidsynth(self) -> bool:
        """Inicializa FluidSynth con el SoundFont."""
        try:
            import fluidsynth
        except ImportError:
            self.error.emit(
                "pyfluidsynth no está instalado.\n"
                "Ejecuta: pip install pyfluidsynth"
            )
            return False

        sf2 = pathlib.Path(self.sf2_path)
        if not sf2.exists():
            self.error.emit(f"SoundFont no encontrado:\n{self.sf2_path}")
            return False

        try:
            self.fs = fluidsynth.Synth()
            # Aumentar polifonía para evitar "Failed to allocate a synthesis process"
            self.fs.setting("synth.polyphony", 512)

            # Delegar el inicio y la anulación de errores a nuestro archivo externo
            from engine.midi_setup import init_fluidsynth
            started = init_fluidsynth(self.fs)

            if not started:
                self.error.emit(
                    "No se pudo iniciar FluidSynth uwu qn sabe pq.\n"
                    "Verifica que las DLLs de FluidSynth estén en la carpeta assets/ por si otro wey se le ocurre eliminar la carpeta xd ."
                )
                return False

        except Exception as e:
            self.error.emit(f"No se pudo inicializar FluidSynth:\n{str(e)}")
            return False

        # Cargar SoundFont y seleccionar programa 0 (Acoustic Grand Piano)
        sfid = self.fs.sfload(str(sf2))
        self.fs.program_select(0, sfid, 0, 0)  # canal 0, bank 0, programa 0
        
        # Ola 3: Activar volumen dinámico real por velocity enviando CC #7 (Volume) y CC #11 (Expression) al canal 0
        try:
            self.fs.cc(0, 7, 127)
            self.fs.cc(0, 11, 127)
        except Exception:
            pass
            
        return True

    def load(self, midi_data: pretty_midi.PrettyMIDI, notes: List[NoteEvent]):
        """Carga datos MIDI para reproducción."""
        self.stop()
        self.midi_data = midi_data
        self.notes = notes
        self.duration = midi_data.get_end_time()
        self.current_time = 0.0
        self._next_note_idx = 0
        self._active_notes.clear()

    def play(self):
        """Inicia o reanuda la reproducción."""
        if self.midi_data is None:
            return

        if self.paused:
            # Reanudar
            self.paused = False
            self.playing = True
            self.start_real_time = time.time() - (self.current_time / self.speed)

            # Re-activar notas que estaban sonando al momento de pausar
            self._active_notes.clear()
            self._next_note_idx = len(self.notes)
            for i, note in enumerate(self.notes):
                if note.start <= self.current_time and note.end > self.current_time:
                    self._note_on(note.pitch, note.velocity)
                    self._active_notes[note.pitch] = note.end
                elif note.start > self.current_time:
                    self._next_note_idx = i
                    break

            self._timer.start()
            self.playback_started.emit()
            return

        # Iniciar desde el principio
        if not self._init_fluidsynth():
            return

        self.playing = True
        self.paused = False
        self.current_time = 0.0
        self._next_note_idx = 0
        self._active_notes.clear()
        self.start_real_time = time.time()
        self._timer.start()
        self.playback_started.emit()

    def pause(self):
        """Pausa la reproducción."""
        if self.playing and not self.paused:
            self.playing = False
            self.paused = True
            self._timer.stop()
            self._all_notes_off()
            self.playback_paused.emit()

    def stop(self):
        """Detiene la reproducción y resetea la posición."""
        self.playing = False
        self.paused = False
        self.current_time = 0.0
        self._next_note_idx = 0
        self._active_notes.clear()
        self._timer.stop()
        self._all_notes_off()
        if self.fs:
            try:
                self.fs.delete()
            except Exception:
                pass
            self.fs = None
        self.playback_stopped.emit()
        self.position_changed.emit(0.0)

    def seek(self, time_sec: float):
        """Mueve la posición de reproducción a un tiempo específico."""
        was_playing = self.playing
        if was_playing:
            self._all_notes_off()

        self.current_time = max(0.0, min(time_sec, self.duration))

        # Recalcular el índice del próximo evento
        self._next_note_idx = 0
        for i, note in enumerate(self.notes):
            if note.end >= self.current_time:
                self._next_note_idx = i
                break

        if was_playing:
            self.start_real_time = time.time() - (self.current_time / self.speed)

        self.position_changed.emit(self.current_time)

    def set_speed(self, speed: float):
        """Ajusta la velocidad de reproducción (0.25x a 2.0x)."""
        was_playing = self.playing
        if was_playing:
            self.start_real_time = time.time() - (self.current_time / self.speed)

        self.speed = max(0.25, min(speed, 2.0))

    def set_volume(self, gain: float):
        """Ajusta el multiplicador de volumen (0.0 – 2.0)."""
        self.volume_gain = max(0.0, min(gain, 2.0))

    def _on_tick(self):
        """Tick del timer: actualiza posición y dispara eventos MIDI."""
        if not self.playing:
            return

        # Calcular tiempo actual
        elapsed_real = time.time() - self.start_real_time
        self.current_time = elapsed_real * self.speed

        # Verificar si llegamos al final
        if self.current_time >= self.duration:
            self._all_notes_off()
            self.playing = False
            self._timer.stop()
            self.current_time = self.duration
            self.position_changed.emit(self.duration)
            self.playback_finished.emit()
            return

        # Procesar note_on: notas que empiezan ahora o antes
        while self._next_note_idx < len(self.notes):
            note = self.notes[self._next_note_idx]
            if note.start > self.current_time:
                break
            # Programar note_on si no empezó antes
            if note.start + note.duration >= self.current_time:
                self._note_on(note.pitch, note.velocity)
                self._active_notes[note.pitch] = note.start + note.duration
            self._next_note_idx += 1

        # Procesar note_off: notas que terminan
        expired = [
            p for p, end_t in self._active_notes.items()
            if end_t <= self.current_time
        ]
        for pitch in expired:
            self._note_off(pitch)
            del self._active_notes[pitch]

        # Emitir posición
        self.position_changed.emit(self.current_time)

    def _note_on(self, pitch: int, velocity: int):
        """Envía note_on a FluidSynth y emite señal con color."""
        from ui.styles import pitch_to_color
        color = pitch_to_color(pitch)

        # Curva Gamma + gain global
        norm = velocity / 127.0
        adjusted_vel = int((norm ** 2.0) * 127 * self.volume_gain)
        adjusted_vel = max(1, min(127, adjusted_vel))

        if self.fs:
            try:
                self.fs.noteon(0, pitch, adjusted_vel)
            except Exception:
                pass
        self.note_on.emit(pitch, velocity, color)

    def _note_off(self, pitch: int):
        """Envía note_off a FluidSynth y emite señal."""
        if self.fs:
            try:
                self.fs.noteoff(0, pitch)
            except Exception:
                pass
        self.note_off.emit(pitch)

    def _all_notes_off(self):
        """Apaga todas las notas activas."""
        if self.fs:
            try:
                self.fs.cc(0, 123, 0)  # All Notes Off
                self.fs.cc(0, 120, 0)  # All Sound Off
            except Exception:
                pass
        for pitch in list(self._active_notes.keys()):
            self.note_off.emit(pitch)
        self._active_notes.clear()
