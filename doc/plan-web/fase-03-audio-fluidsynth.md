# Fase 3: Renderizado de audio con FluidSynth

**Objetivo:** implementar la Opción B: el backend renderiza el MIDI a WAV
con FluidSynth y streamea el audio al frontend.

## 3.1. Dependencias del sistema

```bash
# Ubuntu/Debian
sudo apt-get install fluidsynth libfluidsynth-dev

# macOS
brew install fluid-synth

# Arch
sudo pacman -S fluidsynth
```

SoundFont: `FluidR3_GM.sf2` (ya incluido en `alesito.mix`).

## 3.2. Dependencias de Rust

```toml
fluidsynth = "..."   # o binding a libfluidsynth via FFI
# Alternativa: invocar el binario `fluidsynth` con std::process::Command.
```

Decisión: usar el binario `fluidsynth` por simplicidad y aislamiento de
procesos. Más adelante se puede migrar a binding nativo.

Comando:

```bash
fluidsynth -F salida.wav -r 44100 -g 0.7 FluidR3_GM.sf2 entrada.mid
```

## 3.3. Flujo

```text
Job done (midi_data en memoria)
  -> escribir midi_data a archivo temporal
  -> spawn fluidsynth -> salida.wav
  -> leer salida.wav en memoria
  -> borrar temporales
  -> servir WAV via GET /jobs/:id/audio
```

## 3.4. Endpoint nuevo

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/jobs/:id/audio` | WAV renderizado (audio/wav). |

## 3.5. Cache

- El WAV renderizado se cachea en memoria del job (o en disco temporal)
  para no re-renderizar en cada petición.
- TTL igual al del job.

## 3.6. Pruebas

- Renderizar un MIDI de prueba y verificar que el WAV se reproduce.
- Comparar duración del WAV con `duration_seconds` del job.
- Probar SoundFont faltante (error tipado).

## Entregable

Audio fiel al escritorio, servido por el backend.