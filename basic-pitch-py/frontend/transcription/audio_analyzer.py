"""
audio_analyzer.py — Análisis rápido de audio para auto-ajustar parámetros de transcripción.
Usa librosa para extraer características y calcular los mejores umbrales.
"""

import numpy as np

try:
    import librosa
    LIBROSA_PRESENT = True
except ImportError:
    LIBROSA_PRESENT = False


def analyze_audio(audio_path: str) -> dict:
    """
    Analiza un archivo de audio y retorna los parámetros óptimos de transcripción.
    Retorna dict con: onset_threshold, frame_threshold, minimum_note_length,
                      minimum_frequency, maximum_frequency
    """
    if not LIBROSA_PRESENT:
        return _default_settings()

    try:
        # Cargar audio (máx 30 segundos para análisis rápido)
        y, sr = librosa.load(audio_path, sr=22050, duration=30.0)

        # ── 1. Estimar nivel de ruido ───────────────────────────────────────
        rms = librosa.feature.rms(y=y)[0]
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        noise_floor = np.percentile(rms_db, 10)  # Nivel de ruido (percentil bajo)
        signal_level = np.percentile(rms_db, 90)  # Nivel de señal (percentil alto)
        snr = signal_level - noise_floor  # Relación señal/ruido en dB

        # ── 2. Detectar onset strength ──────────────────────────────────────
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_mean = np.mean(onset_env)
        onset_std = np.std(onset_env)

        # ── 3. Detectar frecuencias dominantes ───────────────────────────────
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        # Filtrar pitches con magnitud significativa
        valid_pitches = []
        for t in range(pitches.shape[1]):
            idx = magnitudes[:, t].argmax()
            if magnitudes[idx, t] > 0:
                p = pitches[idx, t]
                if 30 < p < 5000:
                    valid_pitches.append(p)

        if valid_pitches:
            freq_min_detected = max(30, np.percentile(valid_pitches, 5) * 0.8)
            freq_max_detected = min(8000, np.percentile(valid_pitches, 95) * 1.2)
        else:
            freq_min_detected = 65
            freq_max_detected = 6000

        # ── 4. Estimar densidad de notas ─────────────────────────────────────
        # Usar onset detection para estimar cuántas notas hay por segundo
        onsets = librosa.onset.onset_detect(y=y, sr=sr)
        duration = len(y) / sr
        note_density = len(onsets) / max(duration, 0.1)

        # ── Calcular parámetros óptimos ──────────────────────────────────────

        # Onset threshold: más alto si hay mucho ruido
        if snr < 10:
            onset_threshold = 0.7  # Mucho ruido → ser menos sensible
        elif snr < 20:
            onset_threshold = 0.5  # Ruido moderado
        else:
            onset_threshold = 0.3  # Señal limpia → ser más sensible

        # Frame threshold: más bajo si las notas son largas/sostenidas
        sustain_ratio = _estimate_sustain(y, sr)
        if sustain_ratio > 0.6:
            frame_threshold = 0.2  # Notas largas → capturar más sostén
        elif sustain_ratio > 0.3:
            frame_threshold = 0.3  # Mix
        else:
            frame_threshold = 0.4  # Notas cortas → ser más estricto

        # Minimum note length: más corto si hay muchas notas rápidas
        if note_density > 5:
            min_note_length = 60   # Muchas notas → permitir notas cortas
        elif note_density > 2:
            min_note_length = 100  # Densidad media
        else:
            min_note_length = 150  # Pocas notas → filtrar transitorios

        return {
            "onset_threshold": round(onset_threshold, 2),
            "frame_threshold": round(frame_threshold, 2),
            "minimum_note_length": round(min_note_length, 1),
            "minimum_frequency": round(freq_min_detected),
            "maximum_frequency": round(freq_max_detected),
        }

    except Exception:
        return _default_settings()


def _estimate_sustain(y: np.ndarray, sr: int) -> float:
    """Estima la proporción de audio sostenido vs. transitorio."""
    try:
        # Usar onset envelope para detectar transitorios
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        # Normalizar
        onset_norm = (onset_env - onset_env.min()) / (onset_env.max() - onset_env.min() + 1e-8)
        # Umbral para detectar onsets
        threshold = np.mean(onset_norm) + np.std(onset_norm)
        # Contar frames por encima del umbral (transitorios) vs debajo (sostenidos)
        transient_frames = np.sum(onset_norm > threshold)
        total_frames = len(onset_norm)
        sustain_ratio = 1.0 - (transient_frames / max(total_frames, 1))
        return max(0.0, min(1.0, sustain_ratio))
    except Exception:
        return 0.5


def _default_settings() -> dict:
    """Valores por defecto cuando no se puede analizar."""
    return {
        "onset_threshold": 0.5,
        "frame_threshold": 0.3,
        "minimum_note_length": 127.0,
        "minimum_frequency": 65.0,
        "maximum_frequency": 6000.0,
    }
