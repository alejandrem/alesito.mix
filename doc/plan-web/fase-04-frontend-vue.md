# Fase 4: Frontend Vue mínimo

**Estado: Completada.**

**Objetivo:** interfaz web mínima usable: subir audio, transcribir, ver notas,
reproducir y descargar MIDI.

## Lo que está hecho

- ✅ Vue 3 + TypeScript + Vite.
- ✅ Flujo end-to-end: cargar MP3/MIDI, transcribir audio, mostrar notas, reproducir audio renderizado, descargar MIDI.
- ✅ Polling de estado del job con fallback; también hay soporte WS integrado (ver fase 5).
- ✅ Pinia instalado y store base en `web/src/stores/transcription.ts`.
- ✅ Cliente HTTP con Axios en `web/src/api/client.ts`.
- ✅ Separación inicial de componentes: `UploadPanel`, `TranscribeButton`, `NotesList`, `AudioPlayer`, `DownloadButton`.
- ✅ Piano roll básico ya integrado (`PianoRoll.vue`), adelantando parte de fase 6.

## Notas / deuda no bloqueante

- ⚠️ **Tailwind no está integrado**. El estilo actual sigue en `web/src/style.css` y clases existentes; migrar a Tailwind sería un rewrite grande.
- ⚠️ `App.vue` sigue concentrando bastante orquestación (no está totalmente descompuesto al 100% como sugiere el plan).
- ⚠️ `TranscribeButton.vue` y `AudioPlayer.vue` existen, pero la UI principal todavía usa parte del flujo/botones directamente en `App.vue`.
- ⚠️ La estructura no es idéntica al árbol del plan original, aunque cubre la intención funcional.

## Entregable

Web usable end-to-end. **Completado** para el alcance actual, con deuda técnica/estructura menor no bloqueante.
