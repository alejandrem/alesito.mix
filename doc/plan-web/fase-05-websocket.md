# Fase 5: Progreso en tiempo real (WebSocket)

**Estado: Completada.**

**Objetivo:** comunicar el progreso de la transcripción al frontend sin polling.

## Lo que está hecho

- ✅ Endpoint WebSocket `WS /ws/:id` en backend (`backend/src/main.rs`, `backend/src/routes/transcribe.rs`).
- ✅ Eventos de progreso por job con `broadcast` en `backend/src/state.rs`.
- ✅ Mensajes JSON tipo `progress`, `done`, `error`.
- ✅ Composable frontend `web/src/composables/useJobProgress.ts`.
- ✅ Frontend usa WS y cae a polling si la conexión WS falla.
- ✅ Vite proxy configurado con `ws: true`.
- ✅ Barra de progreso simple en UI cuando hay procesamiento.

## Notas / deuda no bloqueante

- ⚠️ **No hay progreso granular real por ventanas del motor** (`window/total` durante inferencia) porque `basic-pitch-transcription` se usa como caja negra. Hoy se emiten etapas/estados útiles (`queued`, `transcribing`, `done`, `error`), pero no el desglose fino que imagina el plan.
- ⚠️ La UI de progreso es simple (mensaje + barra básica), no el overlay/animación completa estilo desktop.
- ⚠️ No hay reconexión sofisticada con reintentos/backoff más allá del fallback a polling.

## Entregable

Progreso en vivo durante la transcripción. **Completado**: hay canal WS real y fallback a polling; la granularidad fina del motor queda como mejora futura.
