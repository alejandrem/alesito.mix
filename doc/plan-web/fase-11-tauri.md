# Fase 11: Versión de escritorio (Tauri)

**Objetivo:** reutilizar el frontend Vue en una app de escritorio con Tauri,
usando FluidSynth nativo.

## 11.1. Estrategia

- Mismo frontend (`frontend/`).
- Backend Rust embebido en Tauri (comandos en lugar de HTTP).
- FluidSynth nativo (binding o proceso) para audio fiel.
- SQLite local.

## 11.2. Ventajas

- Reutiliza el 90 % del frontend.
- Audio nativo sin streaming.
- Offline.

## 11.3. Cuándo hacerlo

Solo después de que la web tenga paridad mínima (Fases 1-4). No antes.

## Entregable

App de escritorio con la misma UI que la web.