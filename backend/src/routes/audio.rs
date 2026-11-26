use axum::body::Body;
use axum::extract::State;
use axum::http::{Request, StatusCode};
use axum::response::IntoResponse;
use futures::StreamExt;
use tokio::io::AsyncWriteExt;
use uuid::Uuid;

use crate::error::{AppError, AppResult};
use crate::state::AppState;

pub async fn render_midi(
    State(state): State<AppState>,
    request: Request<Body>,
) -> AppResult<impl IntoResponse> {
    let _permit = state
        .audio_render_slots
        .clone()
        .try_acquire_owned()
        .map_err(|_| AppError::TooManyJobs("hay demasiados MIDI en renderizado".into()))?;

    let render_id = Uuid::new_v4();
    let midi_path = state.temp_dir.join(format!("{render_id}.upload.mid"));
    let wav_path = state.temp_dir.join(format!("{render_id}.wav"));
    let mut file = tokio::fs::File::create(&midi_path)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;
    let mut stream = request.into_body().into_data_stream();
    let max_size = state.config.max_audio_size_bytes;

    let write_result: AppResult<()> = async {
        let mut total_size = 0_u64;
        while let Some(chunk) = stream.next().await {
            let chunk = chunk.map_err(|e| AppError::BadRequest(e.to_string()))?;
            total_size = total_size.saturating_add(chunk.len() as u64);
            if total_size > max_size {
                return Err(AppError::BadRequest(format!(
                    "MIDI demasiado grande (maximo {} MB)",
                    max_size / 1024 / 1024
                )));
            }
            file.write_all(&chunk)
                .await
                .map_err(|e| AppError::Internal(e.to_string()))?;
        }

        if total_size == 0 {
            return Err(AppError::BadRequest("el archivo MIDI esta vacio".into()));
        }
        file.flush()
            .await
            .map_err(|e| AppError::Internal(e.to_string()))?;
        Ok(())
    }
    .await;

    if let Err(error) = write_result {
        drop(file);
        let _ = tokio::fs::remove_file(&midi_path).await;
        return Err(error);
    }
    drop(file);

    let soundfont = state.soundfont.clone();
    let timeout_secs = state.config.fluidsynth_timeout_secs;
    let render_midi_path = midi_path.clone();
    let render_wav_path = wav_path.clone();
    let render_result = tokio::task::spawn_blocking(move || {
        crate::audio::render_midi_file_to_wav(
            &render_midi_path,
            &soundfont,
            &render_wav_path,
            timeout_secs,
        )
    })
    .await;
    let _ = tokio::fs::remove_file(&midi_path).await;

    match render_result {
        Ok(Ok(())) => {}
        Ok(Err(error)) => {
            let _ = tokio::fs::remove_file(&wav_path).await;
            return Err(AppError::Internal(error));
        }
        Err(error) => {
            let _ = tokio::fs::remove_file(&wav_path).await;
            return Err(AppError::Internal(format!(
                "fallo la tarea de audio: {error}"
            )));
        }
    }

    let wav = match tokio::fs::read(&wav_path).await {
        Ok(wav) => wav,
        Err(error) => {
            let _ = tokio::fs::remove_file(&wav_path).await;
            return Err(AppError::Internal(error.to_string()));
        }
    };
    let _ = tokio::fs::remove_file(&wav_path).await;

    Ok((StatusCode::OK, [("content-type", "audio/wav")], wav))
}
