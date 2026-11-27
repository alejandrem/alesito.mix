use std::path::{Path, PathBuf};

use serde_json::json;
use uuid::Uuid;

use crate::error::{AppError, AppResult};
use crate::state::{AppState, Job, JobStatus, ProgressEvent};

use super::dto::TranscriptionOptions;
use super::validation::{audio_duration_seconds, is_audio_duration_allowed, validate_options};

pub async fn ensure_job_capacity(state: &AppState) -> AppResult<()> {
    let jobs = state.jobs.read().await;
    if jobs.len() < state.config.max_jobs {
        return Ok(());
    }
    Err(AppError::TooManyJobs(format!(
        "servidor sobrecargado (maximo {} jobs activos)",
        state.config.max_jobs
    )))
}

pub fn cleanup_job_files(job: &Job) {
    remove_path(job.audio_path.as_ref());
    remove_path(job.rendered_audio.as_ref());
}

fn remove_path(path: Option<&PathBuf>) {
    if let Some(path) = path {
        let _ = std::fs::remove_file(path);
    }
}

pub async fn enqueue_new_transcription(
    state: AppState,
    job_id: Uuid,
    audio_path: PathBuf,
    options: TranscriptionOptions,
) -> AppResult<axum::Json<serde_json::Value>> {
    validate_options(&options).map_err(|e| cleanup_and_err(&audio_path, e))?;
    validate_audio_file(&state, &audio_path).await?;
    let progress_tx = create_progress_channel();
    insert_new_job(
        &state,
        job_id,
        audio_path.clone(),
        options,
        progress_tx.clone(),
    )
    .await;
    spawn_transcription_task(state, job_id, audio_path, options, progress_tx);
    Ok(axum::Json(json!({ "job_id": job_id })))
}

pub async fn enqueue_existing_transcription(
    state: AppState,
    job_id: Uuid,
    audio_path: PathBuf,
    options: TranscriptionOptions,
) -> AppResult<axum::Json<serde_json::Value>> {
    validate_options(&options)?;
    let progress_tx = create_progress_channel();
    reset_job(&state, job_id, options, progress_tx.clone()).await;
    spawn_transcription_task(state, job_id, audio_path, options, progress_tx);
    Ok(axum::Json(json!({ "job_id": job_id })))
}

fn cleanup_and_err(audio_path: &PathBuf, err: AppError) -> AppError {
    let _ = std::fs::remove_file(audio_path);
    err
}

async fn validate_audio_file(state: &AppState, audio_path: &PathBuf) -> AppResult<()> {
    let duration = read_duration(audio_path).await?;
    if is_audio_duration_allowed(duration, state.config.max_audio_duration_secs) {
        return Ok(());
    }
    let _ = tokio::fs::remove_file(audio_path).await;
    Err(AppError::BadRequest(format!(
        "audio demasiado largo (máximo {} minutos)",
        state.config.max_audio_duration_secs / 60
    )))
}

async fn read_duration(audio_path: &PathBuf) -> AppResult<f64> {
    let path = audio_path.clone();
    let duration = tokio::task::spawn_blocking(move || audio_duration_seconds(&path))
        .await
        .map_err(|error| {
            let _ = std::fs::remove_file(audio_path);
            AppError::Internal(error.to_string())
        })?;
    duration.map_err(|error| {
        let _ = std::fs::remove_file(audio_path);
        AppError::BadRequest(format!("audio inválido o formato no soportado: {error}"))
    })
}

fn create_progress_channel() -> tokio::sync::broadcast::Sender<ProgressEvent> {
    let (tx, _) = tokio::sync::broadcast::channel(16);
    let _ = tx.send(ProgressEvent::stage("queued", 0));
    tx
}

async fn insert_new_job(
    state: &AppState,
    job_id: Uuid,
    audio_path: PathBuf,
    options: TranscriptionOptions,
    progress_tx: tokio::sync::broadcast::Sender<ProgressEvent>,
) {
    let mut jobs = state.jobs.write().await;
    jobs.insert(
        job_id,
        Job {
            id: job_id,
            status: JobStatus::Queued,
            audio_path: Some(audio_path),
            result: None,
            edited_notes: None,
            edited_midi: None,
            midi_tempo: options.midi_tempo,
            error: None,
            rendered_audio: None,
            created_at: std::time::Instant::now(),
            progress_tx,
        },
    );
}

async fn reset_job(
    state: &AppState,
    job_id: Uuid,
    options: TranscriptionOptions,
    progress_tx: tokio::sync::broadcast::Sender<ProgressEvent>,
) {
    let mut jobs = state.jobs.write().await;
    if let Some(job) = jobs.get_mut(&job_id) {
        job.status = JobStatus::Queued;
        job.result = None;
        job.edited_notes = None;
        job.edited_midi = None;
        job.midi_tempo = options.midi_tempo;
        job.error = None;
        job.rendered_audio = None;
        job.progress_tx = progress_tx;
    }
}

fn spawn_transcription_task(
    state: AppState,
    job_id: Uuid,
    audio_path: PathBuf,
    options: TranscriptionOptions,
    progress_tx: tokio::sync::broadcast::Sender<ProgressEvent>,
) {
    tokio::spawn(async move {
        run_transcription(state, job_id, audio_path, options, progress_tx).await;
    });
}

async fn run_transcription(
    state: AppState,
    job_id: Uuid,
    audio_path: PathBuf,
    options: TranscriptionOptions,
    progress_tx: tokio::sync::broadcast::Sender<ProgressEvent>,
) {
    mark_running(&state, job_id).await;
    let outcome = run_transcriber(&state, &audio_path, options).await;
    apply_transcription_outcome(&state, job_id, outcome, &progress_tx).await;
}

async fn mark_running(state: &AppState, job_id: Uuid) {
    let mut jobs = state.jobs.write().await;
    if let Some(job) = jobs.get_mut(&job_id) {
        job.status = JobStatus::Running;
        let _ = job
            .progress_tx
            .send(ProgressEvent::stage("transcribing", 10));
    }
}

async fn run_transcriber(
    state: &AppState,
    audio_path: &Path,
    options: TranscriptionOptions,
) -> Result<basic_pitch_transcription::TranscriptionResult, String> {
    let mut transcriber = (*state.transcriber).clone();
    apply_options(&mut transcriber, options);
    let path = audio_path.to_path_buf();
    let outcome = tokio::task::spawn_blocking(move || transcriber.transcribe(&path)).await;
    match outcome {
        Ok(Ok(result)) => Ok(result),
        Ok(Err(error)) => Err(error.to_string()),
        Err(error) => Err(format!("tarea cancelada: {error}")),
    }
}

fn apply_options(
    transcriber: &mut basic_pitch_transcription::Transcriber,
    options: TranscriptionOptions,
) {
    transcriber.config.note_detection.onset_threshold = options.onset_threshold;
    transcriber.config.note_detection.frame_threshold = options.frame_threshold;
    transcriber.config.note_detection.minimum_note_length_ms = options.minimum_note_length_ms;
    transcriber.config.note_detection.min_freq = options.min_freq;
    transcriber.config.note_detection.max_freq = options.max_freq;
    transcriber.config.note_detection.melodia_trick = options.melodia_trick;
    transcriber.config.midi_tempo = options.midi_tempo;
    transcriber.config.multiple_pitch_bends = options.multiple_pitch_bends;
}

async fn apply_transcription_outcome(
    state: &AppState,
    job_id: Uuid,
    outcome: Result<basic_pitch_transcription::TranscriptionResult, String>,
    progress_tx: &tokio::sync::broadcast::Sender<ProgressEvent>,
) {
    let mut jobs = state.jobs.write().await;
    let Some(job) = jobs.get_mut(&job_id) else {
        return;
    };
    match outcome {
        Ok(result) => finalize_success(state, job, job_id, result, progress_tx),
        Err(message) => finalize_failure(job, message, progress_tx),
    }
}

fn finalize_success(
    state: &AppState,
    job: &mut Job,
    job_id: Uuid,
    result: basic_pitch_transcription::TranscriptionResult,
    progress_tx: &tokio::sync::broadcast::Sender<ProgressEvent>,
) {
    render_job_audio(state, job, job_id, &result.midi_data);
    let notes = result.notes.len();
    let duration = result.duration_seconds;
    job.result = Some(result);
    job.status = JobStatus::Done;
    let _ = progress_tx.send(ProgressEvent::Done { notes, duration });
}

fn render_job_audio(state: &AppState, job: &mut Job, job_id: Uuid, midi_data: &[u8]) {
    let wav_path = state.temp_dir.join(format!("{job_id}.wav"));
    let timeout_secs = state.config.fluidsynth_timeout_secs;
    match crate::audio::render_midi_to_wav(midi_data, &state.soundfont, &wav_path, timeout_secs) {
        Ok(()) => job.rendered_audio = Some(wav_path),
        Err(error) => {
            let _ = std::fs::remove_file(&wav_path);
            job.error = Some(format!("transcripción lista; audio no disponible: {error}"));
        }
    }
}

fn finalize_failure(
    job: &mut Job,
    message: String,
    progress_tx: &tokio::sync::broadcast::Sender<ProgressEvent>,
) {
    let _ = progress_tx.send(ProgressEvent::Error {
        message: message.clone(),
    });
    job.status = JobStatus::Failed;
    job.error = Some(message);
    cleanup_job_files(job);
    job.audio_path = None;
    job.rendered_audio = None;
}
