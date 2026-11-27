# Build de escritorio (Tauri) - esqueleto

Este documento describe el estado inicial del empaquetado desktop de alesito.mix.

## Objetivo

Generar binarios/instaladores para Linux y Windows desde GitHub Actions, sin necesitar otro dispositivo físico.

## Qué ya está preparado

- `src-tauri/`: esqueleto Tauri v2.
- `backend/src/lib.rs`: backend reusable como librería; `backend/src/main.rs` usa la librería.
- La app Tauri arranca el backend Axum en `127.0.0.1:3000` y en modo release navega el webview a esa URL.
- CI matrix en `.github/workflows/ci.yml` (Ubuntu + Windows).
- Workflow de release en `.github/workflows/release.yml` (Ubuntu + Windows, `tauri-apps/tauri-action`).

## Dependencias de runtime (problemáticas a resolver)

### 1) WebView
- **Windows**: necesita WebView2 Runtime (normalmente ya está en Windows 10/11; el instalador puede bootstrapearlo).
- **Linux**: necesita WebKitGTK (`libwebkit2gtk-4.1-dev` en build; runtime equivalente en la máquina destino).

### 2) FluidSynth
- Hoy el backend llama `fluidsynth` como binario externo.
- Estrategia:
  - Usar `FLUIDSYNTH_BIN` si está definido.
  - Buscar binario bundlado en `resources/bin/fluidsynth(.exe)`.
  - Fallback a `fluidsynth` en PATH.
- Para release real, hay que incluir FluidSynth + DLLs/libs por plataforma en `src-tauri/resources/bin/`.

### 3) Modelo
- No conviene bundlearlo por peso.
- Estrategia: **descargar en primer arranque** al directorio de datos de la app.
- El desktop fija por defecto `MODEL_DIR` a `<app_data>/models/basic-pitch/icassp-2022` si no existe `MODEL_DIR`.
- Pendiente: implementar descarga automática dentro de la app (hoy existe `backend/scripts/update-model.sh` para entorno dev/CLI).

### 4) SoundFont
- `backend/assets/TimGM6mb.sf2` se incluye como recurso Tauri (`resources/assets/`).
- El desktop fija `SOUNDFONT_PATH` si encuentra el recurso bundlado.

## Comandos locales

### Desarrollo web/backend actual
```bash
cd web && npm run dev
```

### Build frontend
```bash
cd web && npm run build
```

### Build backend release
```bash
cd backend && cargo build --release
```

### Tauri (cuando tengas dependencias del sistema instaladas)
```bash
# Linux: requiere webkit2gtk/libsoxr/fluidsynth y toolchain Tauri
# Windows: requiere VS Build Tools + WebView2
cd src-tauri && cargo tauri dev
```

## Pendientes para “funcionar en todas las máquinas”

- Generar íconos reales de Tauri (`cargo tauri icon ...`); los actuales son placeholders.
- Bundlear FluidSynth por plataforma.
- Implementar descarga/validación de modelo en primer arranque.
- Probar instaladores generados por CI en Windows/Linux limpio.
- Firmado/notarización de instaladores (Windows/macOS) si se distribuye públicamente.
