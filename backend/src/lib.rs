pub mod audio;
pub mod error;
pub mod routes;
pub mod state;

use std::net::SocketAddr;
use std::path::PathBuf;

use axum::extract::DefaultBodyLimit;
use axum::http::{header, HeaderValue, Method};
use axum::routing::{get, post};
use axum::Router;
use basic_pitch_transcription::Transcriber;
use tower_http::cors::{AllowOrigin, CorsLayer};
use tower_http::services::{ServeDir, ServeFile};

use crate::routes::audio::render_midi;
use crate::routes::health::health;
use crate::routes::transcribe::{
    create_transcription, create_transcription_audio, get_audio, get_job, get_midi, get_notes,
    retranscribe_job, update_notes, ws_job,
};
use crate::state::AppState;

pub fn multipart_body_limit(max_audio_size_bytes: u64) -> DefaultBodyLimit {
    let max_request_size = max_audio_size_bytes.saturating_add(64 * 1024);
    DefaultBodyLimit::max(usize::try_from(max_request_size).unwrap_or(usize::MAX))
}

fn cors_layer() -> CorsLayer {
    let origins = allowed_origins();
    CorsLayer::new()
        .allow_methods([Method::GET, Method::POST, Method::PUT, Method::OPTIONS])
        .allow_headers([header::CONTENT_TYPE, header::ACCEPT])
        .allow_origin(origins)
}

fn allowed_origins() -> AllowOrigin {
    let raw = std::env::var("CORS_ALLOWED_ORIGINS").unwrap_or_default();
    let trimmed = raw.trim();
    if trimmed == "*" {
        return AllowOrigin::any();
    }
    let origins = parse_origins(trimmed);
    if origins.is_empty() {
        return AllowOrigin::list(default_origins());
    }
    AllowOrigin::list(origins)
}

fn parse_origins(raw: &str) -> Vec<HeaderValue> {
    raw.split(',')
        .map(str::trim)
        .filter(|v| !v.is_empty() && *v != "*")
        .filter_map(|v| v.parse::<HeaderValue>().ok())
        .collect()
}

fn default_origins() -> Vec<HeaderValue> {
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    .into_iter()
    .filter_map(|v| v.parse::<HeaderValue>().ok())
    .collect()
}

pub fn build_router(state: AppState, web_dist_path: Option<PathBuf>) -> Router {
    let mut app = Router::new()
        .route("/health", get(health))
        .route(
            "/transcribe",
            post(create_transcription)
                .layer(multipart_body_limit(state.config.max_audio_size_bytes)),
        )
        .route(
            "/transcribe-audio",
            post(create_transcription_audio)
                .layer(multipart_body_limit(state.config.max_audio_size_bytes)),
        )
        .route("/render-midi", post(render_midi))
        .route("/jobs/:id", get(get_job))
        .route("/jobs/:id/notes", get(get_notes).put(update_notes))
        .route("/jobs/:id/midi", get(get_midi))
        .route("/jobs/:id/audio", get(get_audio))
        .route("/jobs/:id/retranscribe", post(retranscribe_job))
        .route("/ws/:id", get(ws_job))
        .layer(cors_layer())
        .with_state(state);

    if let Some(web_dist_path) = web_dist_path {
        let index = web_dist_path.join("index.html");
        if index.is_file() {
            app = app.fallback_service(
                ServeDir::new(&web_dist_path).not_found_service(ServeFile::new(index)),
            );
        }
    }
    app
}

pub fn resolve_web_dist_dir() -> Option<PathBuf> {
    let web_dist_dir = std::env::var("WEB_DIST_DIR").unwrap_or_else(|_| "../web/dist".to_string());
    let path = PathBuf::from(web_dist_dir);
    if path.join("index.html").is_file() {
        Some(path)
    } else {
        None
    }
}

pub async fn create_state() -> AppState {
    let model_dir = std::env::var("MODEL_DIR")
        .unwrap_or_else(|_| "./models/basic-pitch/icassp-2022".to_string());
    let temp_dir = PathBuf::from(std::env::var("TEMP_DIR").unwrap_or_else(|_| "./tmp".to_string()));
    std::fs::create_dir_all(&temp_dir).expect("no se pudo crear el directorio temporal");
    let transcriber =
        Transcriber::load(std::path::Path::new(&model_dir)).expect("no se pudo cargar el modelo");
    let soundfont = crate::audio::default_soundfont();
    AppState::new(transcriber, temp_dir, soundfont)
}

pub fn spawn_cleanup_task(state: AppState) {
    let cleanup_dir = state.temp_dir.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_secs(300));
        loop {
            interval.tick().await;
            cleanup_expired_jobs(&state).await;
            let _ = &cleanup_dir;
        }
    });
}

async fn cleanup_expired_jobs(state: &AppState) {
    let now = std::time::Instant::now();
    let mut jobs = state.jobs.write().await;
    let expired: Vec<uuid::Uuid> = jobs
        .iter()
        .filter(|(_, j)| now.duration_since(j.created_at).as_secs() > 3600)
        .map(|(id, _)| *id)
        .collect();
    for id in expired {
        if let Some(job) = jobs.remove(&id) {
            remove_job_file(job.audio_path.as_ref());
            remove_job_file(job.rendered_audio.as_ref());
        }
    }
}

fn remove_job_file(path: Option<&PathBuf>) {
    if let Some(path) = path {
        let _ = std::fs::remove_file(path);
    }
}

pub async fn serve(app: Router, addr: SocketAddr) -> std::io::Result<()> {
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await
}
