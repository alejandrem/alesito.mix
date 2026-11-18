# Fase 4: Frontend Vue mínimo

**Objetivo:** interfaz web mínima usable: subir audio, transcribir, ver notas,
reproducir y descargar MIDI.

## 4.1. Stack frontend

- Vue 3 (Composition API) + TypeScript.
- Vite (dev server + build).
- Tailwind CSS.
- Pinia (estado global).
- Axios o fetch para REST.

## 4.2. Estructura

```text
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.js
└── src/
    ├── main.ts
    ├── App.vue
    ├── api/
    │   └── client.ts          # llamadas REST
    ├── stores/
    │   └── transcription.ts   # estado del job
    └── components/
        ├── UploadPanel.vue
        ├── TranscribeButton.vue
        ├── NotesList.vue
        ├── AudioPlayer.vue     # reproduce el WAV del backend
        └── DownloadButton.vue
```

## 4.3. Flujo de la UI mínima

1. Usuario selecciona archivo.
2. Clic en "Transcribir" → `POST /transcribe`.
3. Polling o WebSocket de estado.
4. Al terminar: mostrar notas, habilitar reproducción y descarga.

## 4.4. Reproducción

`<audio>` HTML5 apuntando a `/jobs/:id/audio`. Controles nativos
(play/pause/seek) son suficientes para v1.

## 4.5. Pruebas

- Subir cada formato de audio y transcribir.
- Verificar que el reproductor carga el WAV.
- Verificar descarga del MIDI.

## Entregable

Web usable end-to-end sin piano roll.