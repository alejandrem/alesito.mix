# Fase 9: Exportación y descargas

**Objetivo:** exportar resultados en múltiples formatos.

## 9.1. Formatos

- MIDI (ya disponible).
- WAV renderizado (ya disponible).
- MusicXML (futuro, vía MuseScore CLI en el backend).
- JSON de notas (para integración).

## 9.2. Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/jobs/:id/midi` | Descarga MIDI. |
| `GET` | `/jobs/:id/audio` | Descarga/stream WAV. |
| `GET` | `/jobs/:id/notes?format=json` | Notas en JSON. |

## Entregable

Exportación funcional y descargable.