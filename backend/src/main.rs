mod error;
mod routes;
mod state;

use std::net::SocketAddr;
use std::path::PathBuf;

use axum::routing::{get, post};
use axum::Router;
use basic_pitch_transcription::Transcriber;
use tower_http::cors::CorsLayer;
use tracing_subscriber::EnvFilter;

use crate::routes::health::health;
use crate::routes::transcribe::{
    create_transcription, get_job, get_midi, get_notes,
};
use crate::state::AppState;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let model_dir = std::env::var("MODEL_DIR")
        .unwrap_or_else(|_| "../../basic-pitch-rs/models/basic-pitch/icassp-2022".to_string());
    let temp_dir = PathBuf::from(std::env::var("TEMP_DIR").unwrap_or_else(|_| "./tmp".to_string()));
    std::fs::create_dir_all(&temp_dir).expect("no se pudo crear el directorio temporal");

    let transcriber = Transcriber::load(std::path::Path::new(&model_dir))
        .expect("no se pudo cargar el modelo");

    let state = AppState::new(transcriber, temp_dir);

    let app = Router::new()
        .route("/health", get(health))
        .route("/transcribe", post(create_transcription))
        .route("/jobs/:id", get(get_job))
        .route("/jobs/:id/notes", get(get_notes))
        .route("/jobs/:id/midi", get(get_midi))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr: SocketAddr = "0.0.0.0:3000".parse().unwrap();
    tracing::info!("alesito-backend escuchando en {}", addr);
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}