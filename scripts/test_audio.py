"""
test_audio.py — Prueba rápida de audio con FluidSynth y SoundFont.
Toca un acorde de Do Mayor (C - E - G - C) en el piano para verificar que el sonido funciona.
"""

import sys
import time
import pathlib

# Asegurar path de frontend
repo_root = pathlib.Path(__file__).resolve().parent.parent
frontend_dir = repo_root / "frontend"
sys.path.insert(0, str(frontend_dir))

import fluidsynth
from engine.midi_setup import init_fluidsynth

def main():
    print("Iniciando prueba de sonido...")
    fs = fluidsynth.Synth()
    fs.setting("synth.polyphony", 64)

    if not init_fluidsynth(fs):
        print("[ERROR] No se pudo inicializar ningún driver de audio.")
        sys.exit(1)

    # Buscar soundfont
    sf2_candidates = [
        frontend_dir / "FluidR3_GM.sf2",
        frontend_dir / "TimGM6mb.sf2",
    ]
    sf2_path = None
    for c in sf2_candidates:
        if c.exists():
            sf2_path = str(c)
            break

    if not sf2_path:
        try:
            import pretty_midi
            pm_sf2 = pathlib.Path(pretty_midi.__file__).resolve().parent / "TimGM6mb.sf2"
            if pm_sf2.exists():
                sf2_path = str(pm_sf2)
        except Exception:
            pass

    if not sf2_path:
        print("[ERROR] No se encontró ningún SoundFont (.sf2).")
        sys.exit(1)

    print(f"[INFO] Usando SoundFont: {sf2_path}")
    sfid = fs.sfload(sf2_path)
    fs.program_select(0, sfid, 0, 0)

    # Tocar arpegio C4, E4, G4, C5
    notes = [60, 64, 67, 72]
    print("[INFO] Tocando notas...")
    for n in notes:
        fs.noteon(0, n, 100)
        time.sleep(0.3)

    time.sleep(1.0)
    for n in notes:
        fs.noteoff(0, n)

    print("¡Listo! Si escuchaste las notas, el audio de alesito.mix ya está funcionando perfectamente.")

if __name__ == "__main__":
    main()

