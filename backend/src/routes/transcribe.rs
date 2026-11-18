use axum::extract::{Multipart, Path, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde::Serialize;
use serde_json::json;
use uuid::Uuid;

use crate::error::{AppError, AppResult};
use crate::state::{AppState, Job, JobStatus};

#[derive(Serialize)]
pub struct JobResponse {
    pub id: Uuid,
    pub status: &'static str,
    pub notes_count: Option<usize>,
    pub duration_seconds: Option<f64>,
    pub error: Option<String>,
}

#[derive(Serialize)]
pub struct NoteDto {
    pub start_time: f64,
    pub end_time: f64,
    pub pitch: u8,
    pub velocity: u8,
    pub amplitude: f32,
    pub pitch_bend: Option<Vec<i16>>,
}

pub async fn create_transcription(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> AppResult<Json<serde_json::Value>> {
    // Leer el archivo de audio del multipart.
    let mut audio_bytes: Option<Vec<u8>> = None;
    let mut filename = String::from("audio");
    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(|e| AppError::BadRequest(e.to_string()))?
    {
        if field.name() == Some("audio") {
            filename = field.file_name().unwrap_or("audio").to_string();
            let data = field
                .bytes()
                .await
                .map_err(|e| AppError::BadRequest(e.to_string()))?;
            audio_bytes = Some(data.to_vec());
        }
    }

    let data = audio_bytes.ok_or_else(|| AppError::BadRequest("falta el campo 'audio'".into()))?;

    // Guardar en disco temporal.
    let job_id = Uuid::new_v4();
    let ext = std::path::Path::new(&filename)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("wav");
    let audio_path = state.temp_dir.join(format!("{job_id}.{ext}"));
    tokio::fs::write(&audio_path, &data)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;

    // Crear job.
    {
        let mut jobs = state.jobs.write().await;
        jobs.insert(
            job_id,
            Job {
                id: job_id,
                status: JobStatus::Queued,
                audio_path: Some(audio_path.clone()),
                result: None,
                error: None,
            },
        );
    }

    // Lanzar transcripción en background.
    let state_clone = state.clone();
    tokio::spawn(async move {
        // Marcar como running.
        {
            let mut jobs = state_clone.jobs.write().await;
            if let Some(job) = jobs.get_mut(&job_id) {
                job.status = JobStatus::Running;
            }
        }

        let transcriber = state_clone.transcriber.clone();
        let path = audio_path.clone();
        let outcome = tokio::task::spawn_blocking(move || transcriber.transcribe(&path)).await;

        let mut jobs = state_clone.jobs.write().await;
        if let Some(job) = jobs.get_mut(&job_id) {
            match outcome {
                Ok(Ok(result)) => {
                    job.result = Some(result);
                    job.status = JobStatus::Done;
                }
                Ok(Err(e)) => {
                    job.status = JobStatus::Failed;
                    job.error = Some(e.to_string());
                }
                Err(e) => {
                    job.status = JobStatus::Failed;
                    job.error = Some(format!("tarea cancelada: {e}"));
                }
            }
        }
    });

    Ok(Json(json!({ "job_id": job_id })))
}

pub async fn get_job(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> AppResult<Json<JobResponse>> {
    let jobs = state.jobs.read().await;
    let job = jobs.get(&id).ok_or_else(|| AppError::NotFound("job no encontrado".into()))?;

    let (count, dur) = match &job.result {
        Some(r) => (Some(r.notes.len()), Some(r.duration_seconds)),
        None => (None, None),
    };

    Ok(Json(JobResponse {
        id: job.id,
        status: job.status.as_str(),
        notes_count: count,
        duration_seconds: dur,
        error: job.error.clone(),
    }))
}

pub async fn get_notes(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> AppResult<Json<Vec<NoteDto>>> {
    let jobs = state.jobs.read().await;
    let job = jobs.get(&id).ok_or_else(|| AppError::NotFound("job no encontrado".into()))?;
    let result = job
        .result
        .as_ref()
        .ok_or_else(|| AppError::BadRequest("transcripcion no lista".into()))?;

    let notes = result
        .notes
        .iter()
        .map(|n| NoteDto {
            start_time: n.start_time,
            end_time: n.end_time,
            pitch: n.pitch,
            velocity: n.velocity,
            amplitude: n.amplitude,
            pitch_bend: n.pitch_bend.clone(),
        })
        .collect();

    Ok(Json(notes))
}

pub async fn get_midi(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> AppResult<impl IntoResponse> {
    let jobs = state.jobs.read().await;
    let job = jobs.get(&id).ok_or_else(|| AppError::NotFound("job no encontrado".into()))?;
    let result = job
        .result
        .as_ref()
        .ok_or_else(|| AppError::BadRequest("transcripcion no lista".into()))?;

    Ok((
        StatusCode::OK,
        [("content-type", "audio/midi")],
        result.midi_data.clone(),
    ))
}