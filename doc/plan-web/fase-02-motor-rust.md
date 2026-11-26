# Fase 2: Integración del motor Rust

**Estado: Completada.**

**Objetivo:** conectar el backend Axum con `basic-pitch-transcription` y
validar la paridad con el escritorio.

## 2.1. Dependencia del motor

Opción A (desarrollo): path local.

```toml
basic-pitch-transcription = { git = "https://github.com/alejandrem/basic-pitch-rs", rev = "<commit>" }
# opcionalmente: tag = "vX.Y.Z"
```

> Estado actual en `alesito.mix`: se usa dependencia git fijada por `rev` en `backend/Cargo.toml` para builds reproducibles.

Opción alternativa (desarrollo local cruzado): path.

```toml
# basic-pitch-transcription = { path = "../../basic-pitch-rs/crates/transcription" }
```
basic-pitch-transcription = { git = "https://github.com/alejandrem/basic-pitch-rs", tag = "v0.1.0" }
```

## 2.2. Flujo de transcripción

```text
POST /transcribe (multipart)
  -> guardar audio en directorio temporal
  -> spawn_blocking: transcriptor.transcribe(path)
  -> guardar notes + midi_data en Job
  -> status = done
```

## 2.3. Configuración expuesta al usuario

Se exponen los parámetros del motor:

- `frame_threshold` (0.3 por defecto).
- `melodia_trick` (true por defecto).
- `midi_tempo` (120.0).
- `multiple_pitch_bends` (false).

Se validan rangos antes de ejecutar.

## 2.4. Limpieza

- Los archivos de audio temporales se borran al terminar el job o al
  expirar (TTL configurable, ej. 1 hora).
- Los `midi_data` se mantienen en memoria hasta expiración.

## 2.5. Pruebas

- Transcribir `vocadito_10.wav` y comparar número de notas (28) y MIDI
  con la referencia.
- Probar los 5 formatos de audio.
- Probar parámetros extremos (umbral 0.1, 0.9).

## Entregable

Backend que transcribe con el motor Rust y paridad verificada contra el CLI.