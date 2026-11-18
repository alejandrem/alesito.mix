# Fase 0: Auditoría y decisiones

**Objetivo:** fijar el alcance, el stack y las decisiones de arquitectura
antes de escribir código.

## 0.1. Alcance de la v1 web

Incluye:
- Subir audio (MP3, WAV, OGG, FLAC, M4A).
- Transcribir con el motor Rust (`basic-pitch-rs`).
- Mostrar notas detectadas (lista + piano roll básico).
- Reproducir el resultado (MIDI renderizado a WAV por FluidSynth).
- Descargar el MIDI.

No incluye (v1):
- Edición avanzada de notas (se deja para la Fase 7).
- Partitura (MuseScore) — se evalúa en v2.
- Multi-usuario / autenticación.
- Persistencia de proyectos (Fase 8).

## 0.2. Stack decidido

- Frontend: Vue 3 + TypeScript + Vite + Tailwind CSS + Pinia.
- Backend: Rust + Axum + Tokio.
- Motor: `basic-pitch-transcription` (dependencia git o path).
- Audio: FluidSynth (en el backend) renderizando MIDI → WAV.
- BD: SQLite (solo a partir de la Fase 8).

## 0.3. Decisiones clave

1. **Opción B de audio:** el backend renderiza el MIDI a WAV con FluidSynth
   y streamea el audio. El frontend no sintetiza.
2. **Jobs asíncronos:** transcripciones largas no bloquean la petición HTTP.
3. **Progreso por WebSocket** (Fase 5), no por polling.
4. **El escritorio PyQt6 no se modifica** hasta tener paridad mínima web.
5. **El frontend se reescribe**, no se porta línea por línea.

## 0.4. Riesgos identificados

- FluidSynth en el servidor requiere dependencias del sistema (`libfluidsynth`).
- Renderizar WAV por transcripción consume CPU y disco temporal.
- El piano roll en Canvas con miles de notas requiere virtualización.
- Latencia de red para archivos grandes.

## Entregable

Documento de decisiones firmado (este archivo) y estructura de carpetas creada.