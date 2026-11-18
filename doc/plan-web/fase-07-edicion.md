# Fase 7: Edición de notas y re-transcripción

**Objetivo:** permitir editar notas y re-transcribir con nuevos parámetros.

## 7.1. Edición en el frontend

- Clic derecho → panel flotante (dinámica, figura, pitch).
- Flechas del teclado: ↑/↓ pitch, ←/→ tiempo.
- Supr/Retroceso: eliminar.
- "Afectar a hermanas": aplicar a todas las notas del mismo pitch.

## 7.2. Sincronización con el backend

- Las ediciones viven en el frontend (estado local).
- "Aplicar ajustes" re-envía parámetros al backend y re-transcribe.
- La posición de reproducción se mantiene al re-transcribir.

## 7.3. Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/jobs/:id/retranscribe` | Re-transcribe con nuevos parámetros. |

## Entregable

Edición básica de notas en la web.