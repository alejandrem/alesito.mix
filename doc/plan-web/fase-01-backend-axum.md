# Fase 1: Backend Axum mínimo

**Estado: Completada (con diferencias menores de estructura).**

**Objetivo:** tener un servidor HTTP que reciba audio y devuelva el MIDI
generado por el motor Rust.

## 1.1. Estructura del backend

```text
backend/
├── Cargo.toml
└── src/
    ├── main.rs          # arranque, router, estado compartido
    ├── state.rs         # AppState (Transcriber, jobs)
    ├── routes/
    │   ├── mod.rs
    │   ├── health.rs
    │   └── transcribe.rs
    ├── jobs.rs          # Job, JobStatus, JobStore
    └── error.rs         # AppError -> IntoResponse
```

## 1.2. Dependencias

```toml
[dependencies]
axum = { version = "0.7", features = ["multipart", "ws"] }
tokio = { version = "1", features = ["full"] }
tower-http = { version = "0.5", features = ["cors", "trace"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tracing = "0.1"
tracing-subscriber = "0.3"
uuid = { version = "1", features = ["v4"] }
basic-pitch-transcription = { git = "https://github.com/alejandrem/basic-pitch-rs" }
```

## 1.3. Endpoints de la Fase 1

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado del servidor. |
| `POST` | `/transcribe` | Recibe multipart (`audio`), crea job, devuelve `job_id`. |
| `GET` | `/jobs/:id` | Estado del job. |
| `GET` | `/jobs/:id/midi` | Bytes MIDI cuando está listo. |
| `GET` | `/jobs/:id/notes` | Notas en JSON. |

## 1.4. Gestión de jobs

- `JobStore`: `Arc<RwLock<HashMap<Uuid, Job>>>`.
- `Job`: `id`, `status`, `notes`, `midi_data`, `error`, `created_at`.
- La transcripción se ejecuta en `tokio::task::spawn_blocking` para no
  bloquear el runtime.

## 1.5. Carga del modelo

El `Transcriber` se carga **una vez** al arrancar (`AppState`) y se comparte
con `Arc`. No se recarga por petición.

## 1.6. Pruebas de la fase

- `GET /health` devuelve 200.
- `POST /transcribe` con un WAV de prueba devuelve `job_id`.
- Tras completar, `GET /jobs/:id/midi` devuelve bytes válidos (parseables
  por `midly`).
- Un archivo inexistente / formato inválido devuelve error tipado.

## Notas de implementación real

- `Job`/estado vive en `backend/src/state.rs` (el plan sugería `jobs.rs` separado).
- Además de los endpoints del plan, existen `/transcribe-audio`, `/render-midi` y `/jobs/:id/audio`.
- El backend también sirve `web/dist` si está disponible (`WEB_DIST_DIR`), para un solo puerto en producción.

## Entregable

Servidor que transcribe un audio y devuelve el MIDI. **Cumplido.**