# Plan de implementación: alesito.mix Web

**Proyecto:** migración de alesito.mix (desktop PyQt6) a una aplicación web con
frontend Vue 3 + TypeScript y backend Rust (Axum) sobre el motor
`basic-pitch-rs`.

**Estrategia de audio:** Opción B — el backend renderiza el MIDI a WAV con
FluidSynth y streamea el audio, para que suene idéntico a la app de escritorio.

**Principio rector:** no se toca el escritorio actual hasta tener paridad web.
El escritorio sigue funcionando como referencia y fallback.

---

## Índice de fases

| # | Fase | Estado | Archivo |
|---|---|---|---|
| 0 | Auditoría y decisiones | Completada | [fase-00-auditoria.md](fase-00-auditoria.md) |
| 1 | Backend Axum mínimo | Completada | [fase-01-backend-axum.md](fase-01-backend-axum.md) |
| 2 | Integración del motor Rust | Completada | [fase-02-motor-rust.md](fase-02-motor-rust.md) |
| 3 | Renderizado de audio con FluidSynth | Completada | [fase-03-audio-fluidsynth.md](fase-03-audio-fluidsynth.md) |
| 4 | Frontend Vue mínimo | Completada | [fase-04-frontend-vue.md](fase-04-frontend-vue.md) |
| 5 | Progreso en tiempo real (WebSocket) | Completada | [fase-05-websocket.md](fase-05-websocket.md) |
| 6 | Piano roll interactivo | Completada | [fase-06-piano-roll.md](fase-06-piano-roll.md) |
| 7 | Edición de notas y re-transcripción | Completada | [fase-07-edicion.md](fase-07-edicion.md) |
| 8 | Persistencia y proyectos (SQLite) | Pendiente (solo versión descargable) | [fase-08-sqlite.md](fase-08-sqlite.md) |
| 9 | Exportación y descargas | Pendiente | [fase-09-exportacion.md](fase-09-exportacion.md) |
| 10 | Empaquetado y despliegue | Pendiente | [fase-10-despliegue.md](fase-10-despliegue.md) |
| 11 | Versión de escritorio (Tauri) | Pendiente | [fase-11-tauri.md](fase-11-tauri.md) |

---

## Bloques de trabajo

| Bloque | Fases | Objetivo | Riesgo |
|---|---|---|---|
| W1 | 0 + 1 + 2 | Backend funcional que transcribe y devuelve MIDI | Bajo |
| W2 | 3 + 4 | Audio fiel (FluidSynth) + UI mínima usable | Medio |
| W3 | 5 + 6 + 7 | Experiencia interactiva (progreso, piano roll, edición) | Medio |
| W4 | 8 + 9 + 10 | Persistencia, exportación y despliegue | Bajo |
| W5 | 11 | Desktop con Tauri reutilizando el frontend | Medio |

## Regla de oro

**No se toca `alesito.mix` (PyQt6) hasta que la web tenga paridad mínima.**
El escritorio sigue siendo la referencia funcional y el fallback.