# 🔇 Bug: Sin sonido al reproducir MIDI

**Fecha:** 2026-07-11
**Severidad:** 🔴 CRÍTICO — la app no produce audio
**Archivos involucrados:** `engine/midi_setup.py`, `engine/playback_engine.py`

---

## Síntomas

Al subir un audio y darle Play, la app funcionaba visualmente (piano roll se movía, notas se iluminaban) pero **no salía ningún sonido por las bocinas**. En la terminal aparecían errores:

```
fluidsynth: error: Couldn't find the requested audio driver 'pulse'.
fluidsynth: warning: Failed to allocate a synthesis process. (chan=0,key=62)
```

---

## Causa raíz

**Bug principal en `midi_setup.py`:**

`fluidsynth.Synth.start(driver='pulse')` **no lanza excepción** cuando falla — retorna `0` (falso). El código original solo checaba excepciones:

```python
# CÓDIGO ORIGINAL (ROTO)
for driver in ["pulse", "pulseaudio", "alsa", ...]:
    try:
        fs.start(driver=driver, midi_driver=False)
        started = True  # ← Se marcaba como True aunque fallara
        break
    except Exception:
        continue
```

Resultado: `started = True` pero `fs.audio_driver = None`. FluidSynth creía que arrancó, pero no había driver de audio conectado. Al intentar tocar notas, fallaba silenciosamente con "Failed to allocate a synthesis process".

**Bug secundario:** el driver `"pulse"` no existe — el correcto es `"pulseaudio"`.

---

## Solución aplicada

### 1. `engine/midi_setup.py` — Verificar `audio_driver` después de `start()`

```python
for driver in drivers:
    try:
        fs.start(driver=driver, midi_driver=False)
    except Exception:
        continue
    # fs.start() no lanza excepción si el driver falla — retorna 0.
    # Verificar que el audio driver se conectó realmente.
    if fs.audio_driver is not None:
        print(f"\n[INFO] FluidSynth arrancó con driver '{driver}'.")
        return True
```

### 2. `engine/midi_setup.py` — Orden de drivers por plataforma

```python
if sys.platform == "win32":
    drivers = ["dsound", "wasapi", "winmm", "portaudio"]
elif sys.platform == "darwin":
    drivers = ["coreaudio", "portaudio"]
else:
    drivers = ["pulseaudio", "pipewire", "alsa", "portaudio", "jack"]
```

### 3. `engine/playback_engine.py` — Aumentar polifonía

```python
self.fs = fluidsynth.Synth()
self.fs.setting("synth.polyphony", 512)  # default es 256
```

Esto previene los errores "Failed to allocate a synthesis process" cuando hay muchas notas simultáneas.

---

## Verificación

```bash
# Test completo de FluidSynth
python -c "
import fluidsynth
fs = fluidsynth.Synth()
fs.setting('synth.polyphony', 512)
fs.start(driver='pulseaudio', midi_driver=False)
assert fs.audio_driver is not None, 'Audio driver no arrancó'
sfid = fs.sfload('frontend/FluidR3_GM.sf2')
fs.program_select(0, sfid, 0, 0)
fs.noteon(0, 60, 100)
time.sleep(0.5)
fs.noteoff(0, 60)
print('Audio OK')
"
```

---

## Lección aprendida

`fluidsynth.Synth.start()` retorna `0` en vez de lanzar excepción cuando el driver no existe. Siempre verificar `fs.audio_driver is not None` después de llamar `start()`.
