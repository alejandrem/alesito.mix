mod audio;
mod error;
mod routes;
mod state;

use std::net::SocketAddr;
use std::path::PathBuf;

use axum::extract::DefaultBodyLimit;
use axum::routing::{get, post};
use axum::Router;
use basic_pitch_transcription::Transcriber;
use tower_http::cors::CorsLayer;
use tracing_subscriber::EnvFilter;
use uuid::Uuid;

use crate::routes::audio::render_midi;
use crate::routes::health::health;
use crate::routes::transcribe::{
    create_transcription, create_transcription_audio, get_audio, get_job, get_midi, get_notes,
};
use crate::state::AppState;

fn multipart_body_limit(max_audio_size_bytes: u64) -> DefaultBodyLimit {
    let max_request_size = max_audio_size_bytes.saturating_add(64 * 1024);
    DefaultBodyLimit::max(usize::try_from(max_request_size).unwrap_or(usize::MAX))
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .init();

    let model_dir = std::env::var("MODEL_DIR")
        .unwrap_or_else(|_| "../../basic-pitch-rs/models/basic-pitch/icassp-2022".to_string());
    let temp_dir = PathBuf::from(std::env::var("TEMP_DIR").unwrap_or_else(|_| "./tmp".to_string()));
    std::fs::create_dir_all(&temp_dir).expect("no se pudo crear el directorio temporal");

    let transcriber =
        Transcriber::load(std::path::Path::new(&model_dir)).expect("no se pudo cargar el modelo");

    let soundfont = crate::audio::default_soundfont();
    let state = AppState::new(transcriber, temp_dir.clone(), soundfont);

    // Limpieza periodica de jobs antiguos (TTL 1 hora).
    let cleanup_state = state.clone();
    let cleanup_dir = temp_dir.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_secs(300));
        loop {
            interval.tick().await;
            let now = std::time::Instant::now();
            let mut jobs = cleanup_state.jobs.write().await;
            let expired: Vec<Uuid> = jobs
                .iter()
                .filter(|(_, j)| now.duration_since(j.created_at).as_secs() > 3600)
                .map(|(id, _)| *id)
                .collect();
            for id in expired {
                if let Some(job) = jobs.remove(&id) {
                    // Borrar tanto el audio original como el WAV renderizado.
                    if let Some(path) = job.audio_path {
                        let _ = tokio::fs::remove_file(path).await;
                    }
                    if let Some(path) = job.rendered_audio {
                        let _ = tokio::fs::remove_file(path).await;
                    }
                }
            }
            let _ = cleanup_dir;
        }
    });

    let app = Router::new()
        .route("/health", get(health))
        .route(
            "/transcribe",
            post(create_transcription)
                .layer(multipart_body_limit(state.config.max_audio_size_bytes)),
        )
        .route("/transcribe-audio", post(create_transcription_audio))
        .route("/render-midi", post(render_midi))
        .route("/jobs/:id", get(get_job))
        .route("/jobs/:id/notes", get(get_notes))
        .route("/jobs/:id/midi", get(get_midi))
        .route("/jobs/:id/audio", get(get_audio))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr: SocketAddr = "0.0.0.0:3000".parse().unwrap();
    let listener = match tokio::net::TcpListener::bind(addr).await {
        Ok(listener) => listener,
        Err(error) => {
            tracing::error!(%addr, %error, "no se pudo iniciar el backend");
            std::process::exit(1);
        }
    };
    tracing::info!("alesito-backend escuchando en {}", addr);
    axum::serve(listener, app).await.unwrap();
}

#[cfg(test)]
mod tests {
    use axum::body::Body;
    use axum::extract::Multipart;
    use axum::http::{Request, StatusCode};
    use axum::routing::post;
    use axum::Router;
    use tower::ServiceExt;

    use super::multipart_body_limit;

    async fn receive_upload(mut multipart: Multipart) -> StatusCode {
        while let Some(mut field) = multipart.next_field().await.unwrap() {
            while field.chunk().await.unwrap().is_some() {}
        }
        StatusCode::OK
    }

    async fn receive_raw_upload(body: axum::body::Body) -> StatusCode {
        use futures::StreamExt;

        let mut stream = body.into_data_stream();
        while stream.next().await.is_some() {}
        StatusCode::OK
    }

    #[tokio::test]
    async fn multipart_limit_accepts_audio_larger_than_axums_default() {
        let payload = "x".repeat(3 * 1024 * 1024);
        let body = format!(
            "--boundary\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"sample.mp3\"\r\nContent-Type: audio/mpeg\r\n\r\n{payload}\r\n--boundary--\r\n"
        );
        let app = Router::new().route(
            "/transcribe",
            post(receive_upload).layer(multipart_body_limit(100 * 1024 * 1024)),
        );
        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/transcribe")
                    .header("content-type", "multipart/form-data; boundary=boundary")
                    .body(Body::from(body))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn raw_audio_upload_accepts_more_than_axums_default_limit() {
        let body = "x".repeat(3 * 1024 * 1024);
        let app = Router::new().route("/transcribe-audio", post(receive_raw_upload));
        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/transcribe-audio")
                    .header("content-type", "audio/mpeg")
                    .body(Body::from(body))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }
}
