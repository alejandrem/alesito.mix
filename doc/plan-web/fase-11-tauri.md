# Fase 11: Versión de escritorio (Tauri)

**Estado: En progreso (esqueleto inicial creado).**

**Objetivo:** reutilizar el frontend Vue en una app de escritorio con Tauri,
aprovechando el backend Rust existente.

## 11.1. Estrategia aplicada

- Frontend reutilizado desde `web/` (build en `web/dist`).
- Backend Rust convertido a librería (`backend/src/lib.rs`) y reutilizado por `src-tauri`.
- La app Tauri inicia el backend Axum en `127.0.0.1:3000` y navega el webview a esa URL.
- SoundFont bundlada como recurso; modelo y FluidSynth con estrategia de resolución por entorno.

## 11.2. Lo que ya existe

- ✅ `src-tauri/` (Tauri v2) con config, build, capabilities y bootstrap Rust.
- ✅ CI matrix Linux/Windows (`.github/workflows/ci.yml`).
- ✅ Workflow de release desktop Linux/Windows (`.github/workflows/release.yml`).
- ✅ Documentación inicial: `doc/desktop-build.md`.

## 11.3. Pendientes

- ⚠️ Bundlear FluidSynth por plataforma (`resources/bin/`).
- ⚠️ Descarga automática de modelo en primer arranque.
- ⚠️ Íconos reales de app (los actuales son placeholders).
- ⚠️ Smoke tests reales en Windows/Linux limpio.
- ⚠️ Firmado/notarización de instaladores.

## Entregable

App de escritorio con la misma UI que la web, empaquetada por plataforma.