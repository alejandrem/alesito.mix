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
    let mut frame_threshold: f64 = 0.3;
    let mut melodia_trick: bool = true;
    let mut midi_tempo: f64 = 120.0;
    let mut multiple_pitch_bends: bool = false;

    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(|e| AppError::BadRequest(e.to_string()))?
    {
        match field.name() {
            Some("audio") => {
                filename = field.file_name().unwrap_or("audio").to_string();
                let data = field
                    .bytes()
                    .await
                    .map_err(|e| AppError::BadRequest(e.to_string()))?;
                audio_bytes = Some(data.to_vec());
            }
            Some("frame_threshold") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                frame_threshold = v.parse().map_err(|_| AppError::BadRequest("frame_threshold invalido".into()))?;
            }
            Some("melodia_trick") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                melodia_trick = v == "true" || v == "1";
            }
            Some("midi_tempo") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                midi_tempo = v.parse().map_err(|_| AppError::BadRequest("midi_tempo invalido".into()))?;
            }
            Some("multiple_pitch_bends") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                multiple_pitch_bends = v == "true" || v == "1";
            }
            _ => {}
        }
    }

    let data = audio_bytes.ok_or_else(|| AppError::BadRequest("falta el campo 'audio'".into()))?;

    // Validacion de parametros.
    if !(0.0..=1.0).contains(&frame_threshold) {
        return Err(AppError::BadRequest("frame_threshold fuera de rango".into()));
    }
    if midi_tempo <= 0.0 {
        return Err(AppError::BadRequest("midi_tempo invalido".into()));
    }

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
                rendered_audio: None,
                created_at: std::time::Instant::now(),
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

        let mut transcriber = (*state_clone.transcriber).clone();
        transcriber.config.note_detection.frame_threshold = frame_threshold;
        transcriber.config.note_detection.melodia_trick = melodia_trick;
        transcriber.config.midi_tempo = midi_tempo;
        transcriber.config.multiple_pitch_bends = multiple_pitch_bends;

        let path = audio_path.clone();
        let outcome = tokio::task::spawn_blocking(move || transcriber.transcribe(&path)).await;

        let mut jobs = state_clone.jobs.write().await;
        if let Some(job) = jobs.get_mut(&job_id) {
            match outcome {
                Ok(Ok(result)) => {
                    let wav_path = state_clone.temp_dir.join(format!("{job_id}.wav"));
                    match crate::audio::render_midi_to_wav(&result.midi_data, &state_clone.soundfont, &wav_path) {
                        Ok(()) => {
                            job.result = Some(result);
                            job.rendered_audio = Some(wav_path);
                            job.status = JobStatus::Done;
                        }
                        Err(e) => {
                            job.status = JobStatus::Failed;
                            job.error = Some(format!("render audio: {e}"));
                        }
                    }
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

pub async fn get_audio(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> AppResult<impl IntoResponse> {
    let jobs = state.jobs.read().await;
    let job = jobs.get(&id).ok_or_else(|| AppError::NotFound("job no encontrado".into()))?;
    let path = job
        .rendered_audio
        .clone()
        .ok_or_else(|| AppError::BadRequest("audio no listo".into()))?;
    drop(jobs);

    let bytes = tokio::fs::read(&path)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;

    Ok((
        StatusCode::OK,
        [("content-type", "audio/wav")],
        bytes,
    ))
}