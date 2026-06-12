"""
midi_parser.py — Convierte PrettyMIDI a eventos de nota simplificados para visualización.
"""

from dataclasses import dataclass
from typing import List

import pretty_midi


@dataclass
class NoteEvent:
    """Evento de nota simplificado para el piano roll."""
    pitch: int        # MIDI pitch (21-108)
    start: float      # tiempo de inicio en segundos
    end: float        # tiempo de fin en segundos
    velocity: int     # 0-127
    color: str = ""   # color de octava (se llena desde styles.py)

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def pitch_name(self) -> str:
        from ui.styles import pitch_to_name
        return pitch_to_name(self.pitch)


def parse_midi(midi_data: pretty_midi.PrettyMIDI) -> List[NoteEvent]:
    """
    Extrae todas las notas de un objeto PrettyMIDI y retorna una lista
    de NoteEvent ordenada por tiempo de inicio.
    """
    from ui.styles import pitch_to_color, PIANO_LOWEST_PITCH, PIANO_HIGHEST_PITCH

    notes = []
    for instrument in midi_data.instruments:
        if instrument.is_drum:
            continue
        for note in instrument.notes:
            pitch = note.pitch
            if pitch < PIANO_LOWEST_PITCH or pitch > PIANO_HIGHEST_PITCH:
                continue
            event = NoteEvent(
                pitch=pitch,
                start=note.start,
                end=note.end,
                velocity=note.velocity,
                color=pitch_to_color(pitch),
            )
            notes.append(event)

    notes.sort(key=lambda n: (n.start, n.pitch))
    return notes


def get_midi_duration(midi_data: pretty_midi.PrettyMIDI) -> float:
    """Retorna la duración total del MIDI en segundos."""
    return midi_data.get_end_time()


def get_midi_info(midi_data: pretty_midi.PrettyMIDI) -> dict:
    """Retorna información resumida del MIDI."""
    notes = parse_midi(midi_data)
    pitches = [n.pitch for n in notes]
    try:
        tempo = midi_data.estimate_tempo()
    except ValueError:
        tempo = 0.0
    return {
        "duration": midi_data.get_end_time(),
        "num_notes": len(notes),
        "num_instruments": len([i for i in midi_data.instruments if not i.is_drum]),
        "pitch_min": min(pitches) if pitches else 0,
        "pitch_max": max(pitches) if pitches else 0,
        "tempo": tempo,
    }
