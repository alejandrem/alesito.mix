# alesito.mix

Transcriptor de audio a MIDI con visualización tipo piano roll. El proyecto está en transición desde un prototipo de escritorio (Python/PyQt6) hacia una arquitectura web: **backend Rust (Axum)** + **frontend Vue 3 + TypeScript + Vite**.

> Estado: **en desarrollo activo**. La dirección principal actual es `backend/` + `web/`. La carpeta `basic-pitch-py/` se conserva como referencia/legacy del prototipo de escritorio.

## Qué hace hoy

- **Transcripción audio → notas/MIDI** usando el motor Rust de [`basic-pitch-rs`](https://github.com/alejandrem/basic-pitch-rs).
- **API backend** para crear jobs de transcripción, consultar estado, obtener notas, descargar MIDI y renderizar audio.
- **Frontend web** para cargar audio/MIDI, visualizar notas en un piano roll y reproducir audio renderizado.
- **Render MIDI → WAV** en backend con FluidSynth y SoundFont propia (`backend/assets/TimGM6mb.sf2`).

## Estructura del repo

```text
.
├── backend/                 # API Rust (Axum, Tokio)
│   ├── assets/              # SoundFont y licencias para render
│   └── src/
│       ├── routes/          # /health, /transcribe, /jobs/:id/*
│       ├── audio.rs
│       ├── state.rs
│       └── main.rs
├── web/                     # Frontend Vue 3 + TS + Vite
│   ├── src/
│   ├── tests/
│   └── scripts/dev.js       # Levanta web + backend juntos
├── basic-pitch-py/          # Prototipo desktop PyQt6 (legacy/referencia)
├── doc/plan-web/            # Plan de migración por fases
└── README.md
```

## Requisitos

### Para la versión web (actual)

- **Rust** estable (edition 2021, recomendado toolchain reciente).
- **Node.js** + npm.
- **FluidSynth** instalado en el sistema (el backend lo usa para renderizar MIDI a WAV).
- **libsoxr** y `pkg-config` (requerido por `basic-pitch-rs` para remuestreo de alta calidad).
- **Modelo de Basic Pitch** disponible localmente (`MODEL_DIR`).

Dependencias de sistema típicas:

```bash
# Arch / CachyOS
sudo pacman -S fluidsynth soxr pkgconf

# Debian / Ubuntu
sudo apt install fluidsynth libsoxr-dev pkg-config
```

## Quickstart (web + backend)

### En esta PC / setup limpio

```bash
# 1) Clona el repo (en otra PC)
git clone https://github.com/alejandrem/alesito.mix.git
cd alesito.mix

# 2) Instala dependencias del frontend
cd web && npm install && cd ..

# 3) Descarga el modelo desde GitHub Releases (una vez)
./backend/scripts/update-model.sh

# 4) Levanta web + backend
cd web && npm run dev
```

> No necesitas tener `basic-pitch-rs` clonado localmente: el código Rust de los crates se descarga desde GitHub por Cargo (`git + rev` en `backend/Cargo.toml`), y los pesos del modelo se descargan desde Releases con el script.

`npm run dev` levanta Vite y el backend Rust (`cargo run --release`) juntos. Vite proxyea `/api` a `http://127.0.0.1:3000`.

Comandos útiles:

```bash
# Actualizar modelo a la última release
./backend/scripts/update-model.sh

# Actualizar modelo a una release específica
./backend/scripts/update-model.sh v0.1.0

# Solo frontend
cd web && npm run dev:web

# Solo backend
cd backend && cargo run --release

# Tests web
cd web && npm test

# Build web
cd web && npm run build
```

## Configuración del backend

Variables de entorno relevantes:

| Variable | Default | Descripción |
| --- | --- | --- |
| `MODEL_DIR` | `./models/basic-pitch/icassp-2022` | Ruta al modelo `icassp-2022` de basic-pitch-rs |
| `TEMP_DIR` | `./tmp` | Directorio temporal para audio/MIDI/WAV |
| `SOUNDFONT_PATH` | `backend/assets/TimGM6mb.sf2` | SoundFont para render MIDI |
| `MAX_JOBS` | `50` | Máximo de jobs activos en memoria |
| `MAX_AUDIO_SIZE_MB` | `100` | Tamaño máximo de audio |
| `MAX_AUDIO_DURATION_SECS` | `720` | Duración máxima de audio (12 min) |
| `FLUIDSYNTH_TIMEOUT_SECS` | `120` | Timeout de render |
| `WEB_DIST_DIR` | `../web/dist` | Si existe `index.html` ahí, el backend sirve el frontend en el mismo puerto |

## Dependencia clave: `basic-pitch-rs`

El backend depende de crates del repo hermano [`alejandrem/basic-pitch-rs`](https://github.com/alejandrem/basic-pitch-rs):

- `basic-pitch-transcription`
- `basic-pitch-midi-io`

### Estado actual (recomendado)

En `backend/Cargo.toml` estas dependencias están configuradas como **dependencias git fijadas por `rev`** para que el build sea reproducible al clonar este repo.

```toml
basic-pitch-transcription = { git = "https://github.com/alejandrem/basic-pitch-rs", rev = "..." }
basic-pitch-midi-io = { git = "https://github.com/alejandrem/basic-pitch-rs", rev = "..." }
```

### Modelo (runtime): se actualiza desde Releases

Los pesos del modelo **no** necesitan el código fuente de `basic-pitch-rs`; se descargan desde los **GitHub Releases** del repo. Esto separa bien las dos cosas:

- **Código Rust** (crates de inferencia): dependencia git en `backend/Cargo.toml`. Cargo lo compila desde fuente.
- **Pesos del modelo** (`.safetensors`, config, checksums): artefactos de runtime descargados desde Releases.

Descargar/actualizar modelo (un comando):

```bash
# Última release
./backend/scripts/update-model.sh

# Release específica
./backend/scripts/update-model.sh v0.1.0
```

El script descarga los assets (`cqt_kernels.safetensors`, `model.safetensors`, `model_config.json`, `SHA256SUMS`, `source_metadata.json`), verifica `sha256sum` y los instala en `backend/models/basic-pitch/icassp-2022/`. Esa carpeta está ignorada por git.

### Actualizar el código de la red neuronal (crates Rust)

Cuando actualices los crates en `basic-pitch-rs`, en este repo solo hace falta actualizar la dependencia:

```bash
cd backend
cargo update -p basic-pitch-transcription -p basic-pitch-midi-io
cargo build --release
```

Si prefieres fijar una versión exacta, cambia el `rev` (o usa `tag = "vX.Y.Z"`) en `backend/Cargo.toml`. Para seguir la rama principal automáticamente (menos reproducible, pero más cómodo en desarrollo) puedes usar `branch = "master"`, pero yo recomiendo mantener `rev/tag` y actualizar con `cargo update` cuando quieras.

## API backend (resumen)

- `GET /health`
- `POST /transcribe` (multipart audio)
- `POST /transcribe-audio`
- `POST /render-midi`
- `GET /jobs/:id`
- `GET /jobs/:id/notes`
- `GET /jobs/:id/midi`
- `GET /jobs/:id/audio`

## Legacy: prototipo desktop Python

La carpeta `basic-pitch-py/` contiene el prototipo original con PyQt6 + basic-pitch (Python) + FluidSynth. Se mantiene como referencia histórica y para comparar comportamiento, pero **no es la ruta principal de desarrollo**.

Si quieres explorarlo, revisa su código y documentación interna en `basic-pitch-py/alesito.md 🎹/` antes de ejecutarlo; el README anterior de raíz estaba centrado en esa versión y quedó desactualizado.

## Plan de migración

La hoja de ruta web está en [`doc/plan-web/`](doc/plan-web/), con fases desde auditoría hasta despliegue/Tauri.

## Licencia

Ver [LICENSE](LICENSE).
