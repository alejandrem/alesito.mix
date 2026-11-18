# Fase 5: Progreso en tiempo real (WebSocket)

**Objetivo:** comunicar el progreso de la transcripción al frontend sin polling.

## 5.1. Protocolo

Endpoint: `WS /ws/:id`.

Mensajes (JSON):

```json
{ "type": "progress", "stage": "decoding", "percent": 10 }
{ "type": "progress", "stage": "transcribing", "percent": 45, "window": 12, "total": 30 }
{ "type": "done", "notes": 1842, "duration": 163.71 }
{ "type": "error", "message": "..." }
```

## 5.2. Backend

- Axum WebSocket upgrade.
- Canal `tokio::sync::mpsc` entre el job y el socket.
- El motor reporta progreso por ventana (requiere extender `Transcriber`
  con un callback o canal; evaluar en esta fase).

## 5.3. Frontend

- Composable `useJobProgress(jobId)`.
- Barra de progreso + mensajes animados (como el overlay del escritorio).
- Reconexión automática si se pierde la conexión.

## Entregable

Progreso en vivo durante la transcripción.