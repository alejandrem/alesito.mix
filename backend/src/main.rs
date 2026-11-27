use std::net::SocketAddr;

use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .init();

    let state = alesito_backend::create_state().await;
    alesito_backend::spawn_cleanup_task(state.clone());

    let web_dist = alesito_backend::resolve_web_dist_dir();
    if let Some(path) = &web_dist {
        tracing::info!("sirviendo frontend desde {}", path.display());
    } else {
        tracing::info!("frontend estático no encontrado; solo API.");
    }

    let app = alesito_backend::build_router(state, web_dist);
    let addr: SocketAddr = "0.0.0.0:3000".parse().unwrap();

    match tokio::net::TcpListener::bind(addr).await {
        Ok(listener) => {
            tracing::info!("alesito-backend escuchando en {}", addr);
            axum::serve(listener, app).await.unwrap();
        }
        Err(error) => {
            tracing::error!(%addr, %error, "no se pudo iniciar el backend");
            std::process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    use axum::body::Body;
    use axum::extract::Multipart;
    use axum::http::{Request, StatusCode};
    use axum::routing::post;
    use axum::Router;
    use tower::ServiceExt;

    use alesito_backend::multipart_body_limit;

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
        let app = Router::new().route(
            "/transcribe-audio",
            post(receive_raw_upload).layer(multipart_body_limit(100 * 1024 * 1024)),
        );
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
