# Fase 10: Empaquetado y despliegue

**Objetivo:** desplegar la web en un servidor.

## 10.1. Build

- Frontend: `npm run build` → `dist/`.
- Backend: `cargo build --release`.
- El backend sirve los archivos estáticos de `dist/` (fallback SPA).

## 10.2. Docker

```dockerfile
# Multi-stage: build frontend + backend, runtime con fluidsynth.
```

Requiere `libfluidsynth` y el SoundFont en la imagen.

## 10.3. Variables de entorno

- `MODEL_DIR`: ruta al modelo.
- `SOUNDFONT_PATH`: ruta al `.sf2`.
- `DATABASE_URL`: SQLite.
- `PORT`.

## 10.4. CI/CD

- GitHub Actions: build frontend, build backend, tests, Docker push.

## Entregable

Web desplegable con un solo comando.