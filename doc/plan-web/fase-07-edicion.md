# Fase 7: Edición de notas y re-transcripción

**Estado: Completada.**

**Objetivo:** permitir editar notas y re-transcribir con nuevos parámetros.

## 7.1. Edición en el frontend

- ✅ Clic derecho sobre una nota → modal/panel de edición (dinámica, figura, pitch/octava).
- ✅ Arrastrar notas en el piano roll para mover pitch/tiempo (preview + commit).
- ✅ Supr/Retroceso: eliminar nota seleccionada.
- ✅ `Ctrl/Cmd + Z`: deshacer cambios de edición.
- ✅ "Aplicar a hermanas": aplicar cambios a todas las notas del mismo pitch.
- ⚠️ Movimiento fino con flechas del teclado (↑/↓ pitch, ←/→ tiempo) queda como mejora futura.

## 7.2. Sincronización con el backend

- ✅ Las ediciones se reflejan en el estado local del frontend.
- ✅ `PUT /jobs/:id/notes` guarda notas editadas, regenera MIDI y vuelve a renderizar audio WAV.
- ✅ "Aplicar ajustes" re-transcribe con nuevos parámetros.
- ✅ La posición de reproducción se preserva al re-transcribir/guardar ediciones.

## 7.3. Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/jobs/:id/retranscribe` | Re-transcribe con nuevos parámetros. |
| `PUT` | `/jobs/:id/notes` | Guarda notas editadas y regenera MIDI/audio. |
| `GET` | `/jobs/:id/notes` | Obtiene notas actuales (originales o editadas). |

## Entregable

Edición básica de notas en la web. **Completado** para el alcance actual.