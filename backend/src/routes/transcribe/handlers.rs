use axum::body::Body;
use axum::extract::{Multipart, Path, Query, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use tokio_util::io::ReaderStream;
use uuid::Uuid;

use crate::error::{AppError, AppResult};
use crate::state::{AppState, JobStatus};

use super::dto::{note_to_dto, JobResponse, NoteDto, TranscriptionOptions, TranscriptionQuery};
use super::jobs::{enqueue_existing_transcription, enqueue_new_transcription, ensure_job_capacity};

pub async fn create_transcription(
    State(state): State<AppState>,
    multipart: Multipart,
) -> AppResult<Json<serde_json::Value>> {
    ensure_job_capacity(&state).await?;
    let job_id = Uuid::new_v4();
    let (audio_path, options) = parse_multipart_upload(&state, job_id, multipart).await?;
    enqueue_new_transcription(state, job_id, audio_path, options).await
}

pub async fn create_transcription_audio(
    State(state): State<AppState>,
    Query(query): Query<TranscriptionQuery>,
    body: Body,
) -> AppResult<Json<serde_json::Value>> {
    ensure_job_capacity(&state).await?;
    let job_id = Uuid::new_v4();
    let audio_path = state.temp_dir.join(format!("{job_id}.audio"));
    stream_body_to_file(body, &audio_path, state.config.max_audio_size_bytes).await?;
    let options = query.apply(TranscriptionOptions::default());
    enqueue_new_transcription(state, job_id, audio_path, options).await
}

async fn parse_multipart_upload(
    state: &AppState,
    job_id: Uuid,
    mut multipart: Multipart,
) -> AppResult<(std::path::PathBuf, TranscriptionOptions)> {
    let mut options = TranscriptionOptions::default();
    let mut audio_path = None;
    while let Some(field) = next_field(&mut multipart).await? {
        audio_path = handle_multipart_field(state, job_id, field, &mut options, audio_path).await?;
    }
    let audio_path =
        audio_path.ok_or_else(|| AppError::BadRequest("falta el campo 'audio'".into()))?;
    Ok((audio_path, options))
}

async fn next_field(
    multipart: &mut Multipart,
) -> AppResult<Option<axum::extract::multipart::Field<'_>>> {
    multipart
        .next_field()
        .await
        .map_err(|e| AppError::BadRequest(e.to_string()))
}

async fn handle_multipart_field(
    state: &AppState,
    job_id: Uuid,
    mut field: axum::extract::multipart::Field<'_>,
    options: &mut TranscriptionOptions,
    audio_path: Option<std::path::PathBuf>,
) -> AppResult<Option<std::path::PathBuf>> {
    let Some(name) = field.name().map(str::to_owned) else {
        return Ok(audio_path);
    };
    if name == "audio" {
        let path = save_audio_field(state, job_id, &mut field).await?;
        return Ok(Some(path));
    }
    let text = field
        .text()
        .await
        .map_err(|e| AppError::BadRequest(e.to_string()))?;
    apply_text_option(&name, &text, options)?;
    Ok(audio_path)
}

async fn save_audio_field(
    state: &AppState,
    job_id: Uuid,
    field: &mut axum::extract::multipart::Field<'_>,
) -> AppResult<std::path::PathBuf> {
    let filename = field.file_name().unwrap_or("audio").to_string();
    let ext = audio_extension(&filename);
    let path = state.temp_dir.join(format!("{job_id}.{ext}"));
    stream_field_to_file(field, &path, state.config.max_audio_size_bytes).await?;
    Ok(path)
}

fn audio_extension(filename: &str) -> &str {
    std::path::Path::new(filename)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("wav")
}

fn apply_text_option(name: &str, value: &str, options: &mut TranscriptionOptions) -> AppResult<()> {
    match name {
        "onset_threshold" => options.onset_threshold = parse_f64(name, value)?,
        "frame_threshold" => options.frame_threshold = parse_f64(name, value)?,
        "minimum_note_length_ms" => options.minimum_note_length_ms = parse_f64(name, value)?,
        "min_freq" => options.min_freq = Some(parse_f64(name, value)?),
        "max_freq" => options.max_freq = Some(parse_f64(name, value)?),
        "melodia_trick" => options.melodia_trick = value == "true" || value == "1",
        "midi_tempo" => options.midi_tempo = parse_f64(name, value)?,
        "multiple_pitch_bends" => options.multiple_pitch_bends = value == "true" || value == "1",
        _ => {}
    }
    Ok(())
}

fn parse_f64(name: &str, value: &str) -> AppResult<f64> {
    value
        .parse()
        .map_err(|_| AppError::BadRequest(format!("{name} invalido")))
}

async fn stream_field_to_file(
    field: &mut axum::extract::multipart::Field<'_>,
    path: &std::path::Path,
    max_size: u64,
) -> AppResult<()> {
    let mut file = tokio::fs::File::create(path)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;
    let mut total_size = 0u64;
    while let Some(chunk) = field
        .chunk()
        .await
        .map_err(|e| AppError::BadRequest(e.to_string()))?
    {
        total_size += chunk.len() as u64;
        ensure_size(total_size, max_size, path).await?;
        write_chunk(&mut file, &chunk, path).await?;
    }
    Ok(())
}

async fn stream_body_to_file(body: Body, path: &std::path::Path, max_size: u64) -> AppResult<()> {
    use futures::StreamExt;
    let mut file = tokio::fs::File::create(path)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;
    let mut total_size = 0u64;
    let mut stream = body.into_data_stream();
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.map_err(|e| cleanup_bad_request(path, e.to_string()))?;
        total_size += chunk.len() as u64;
        ensure_size(total_size, max_size, path).await?;
        write_chunk(&mut file, &chunk, path).await?;
    }
    Ok(())
}

fn cleanup_bad_request(path: &std::path::Path, msg: String) -> AppError {
    let _ = std::fs::remove_file(path);
    AppError::BadRequest(msg)
}

async fn ensure_size(total_size: u64, max_size: u64, path: &std::path::Path) -> AppResult<()> {
    if total_size <= max_size {
        return Ok(());
    }
    let _ = tokio::fs::remove_file(path).await;
    Err(AppError::BadRequest(format!(
        "audio demasiado grande (maximo {} MB)",
        max_size / 1024 / 1024
    )))
}

async fn write_chunk(
    file: &mut tokio::fs::File,
    chunk: &[u8],
    path: &std::path::Path,
) -> AppResult<()> {
    use tokio::io::AsyncWriteExt;
    file.write_all(chunk).await.map_err(|e| {
        let _ = std::fs::remove_file(path);
        AppError::Internal(e.to_string())
    })
}

pub async fn get_job(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> AppResult<Json<JobResponse>> {
    let jobs = state.jobs.read().await;
    let job = jobs.get(&id).ok_or_else(not_found_job)?;
    let (notes_count, duration_seconds) = job_counts(job);
    Ok(Json(JobResponse {
        id: job.id,
        status: job.status.as_str(),
        notes_count,
        duration_seconds,
        error: job.error.clone(),
    }))
}

fn job_counts(job: &crate::state::Job) -> (Option<usize>, Option<f64>) {
    if let Some(edited) = &job.edited_notes {
        let base = job
            .result
            .as_ref()
            .map(|r| r.duration_seconds)
            .unwrap_or(0.0);
        let duration = edited.iter().map(|n| n.end_time).fold(base, f64::max);
        return (Some(edited.len()), Some(duration));
    }
    match &job.result {
        Some(r) => (Some(r.notes.len()), Some(r.duration_seconds)),
        None => (None, None),
    }
}

pub async fn get_notes(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> AppResult<Json<Vec<NoteDto>>> {
    let jobs = state.jobs.read().await;
    let job = jobs.get(&id).ok_or_else(not_found_job)?;
    if let Some(edited) = &job.edited_notes {
        return Ok(Json(edited.iter().map(note_to_dto).collect()));
    }
    let result = job
        .result
        .as_ref()
        .ok_or_else(|| AppError::BadRequest("transcripcion no lista".into()))?;
    Ok(Json(result.notes.iter().map(note_to_dto).collect()))
}

pub async fn get_midi(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> AppResult<impl IntoResponse> {
    let jobs = state.jobs.read().await;
    let job = jobs.get(&id).ok_or_else(not_found_job)?;
    let midi = midi_bytes(job)?;
    Ok((StatusCode::OK, [("content-type", "audio/midi")], midi))
}

fn midi_bytes(job: &crate::state::Job) -> AppResult<Vec<u8>> {
    if let Some(edited) = &job.edited_midi {
        return Ok(edited.clone());
    }
    let result = job
        .result
        .as_ref()
        .ok_or_else(|| AppError::BadRequest("transcripcion no lista".into()))?;
    Ok(result.midi_data.clone())
}

pub async fn get_audio(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> AppResult<impl IntoResponse> {
    let path = audio_path_for_job(&state, id).await?;
    let file = tokio::fs::File::open(&path)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;
    let stream = ReaderStream::new(file);
    let body = Body::from_stream(stream);
    Ok((StatusCode::OK, [("content-type", "audio/wav")], body))
}

async fn audio_path_for_job(state: &AppState, id: Uuid) -> AppResult<std::path::PathBuf> {
    let jobs = state.jobs.read().await;
    let job = jobs.get(&id).ok_or_else(not_found_job)?;
    job.rendered_audio
        .clone()
        .ok_or_else(|| AppError::BadRequest("audio no listo".into()))
}

pub async fn retranscribe_job(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Query(query): Query<TranscriptionQuery>,
) -> AppResult<Json<serde_json::Value>> {
    ensure_job_capacity(&state).await?;
    let audio_path = prepare_retranscribe(&state, id).await?;
    let options = query.apply(TranscriptionOptions::default());
    enqueue_existing_transcription(state, id, audio_path, options).await
}

async fn prepare_retranscribe(state: &AppState, id: Uuid) -> AppResult<std::path::PathBuf> {
    let (audio_path, prev_rendered) = read_retranscribe_job(state, id).await?;
    if let Some(path) = prev_rendered {
        let _ = tokio::fs::remove_file(path).await;
    }
    Ok(audio_path)
}

async fn read_retranscribe_job(
    state: &AppState,
    id: Uuid,
) -> AppResult<(std::path::PathBuf, Option<std::path::PathBuf>)> {
    let jobs = state.jobs.read().await;
    let job = jobs.get(&id).ok_or_else(not_found_job)?;
    if matches!(job.status, JobStatus::Queued | JobStatus::Running) {
        return Err(AppError::BadRequest("el job ya está en ejecución".into()));
    }
    let audio = job.audio_path.clone().ok_or_else(|| {
        AppError::BadRequest(
            "el audio original ya no está disponible; vuelve a subir el archivo".into(),
        )
    })?;
    Ok((audio, job.rendered_audio.clone()))
}

fn not_found_job() -> AppError {
    AppError::NotFound("job no encontrado".into())
}

pub async fn update_notes(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(notes): Json<Vec<NoteDto>>,
) -> AppResult<Json<Vec<NoteDto>>> {
    let ctx = note_update_context(&state, id).await?;
    let cleaned = clean_notes(notes)?;
    let midi_data = build_midi(&cleaned, ctx.midi_tempo)?;
    let render_result = render_updated_audio(&ctx, &midi_data).await?;
    apply_note_update(
        &state,
        id,
        cleaned.clone(),
        midi_data,
        ctx.wav_path,
        render_result,
    )
    .await?;
    Ok(Json(cleaned.iter().map(note_to_dto).collect()))
}

struct NoteUpdateContext {
    midi_tempo: f64,
    soundfont: std::path::PathBuf,
    timeout_secs: u64,
    wav_path: std::path::PathBuf,
}

async fn note_update_context(state: &AppState, id: Uuid) -> AppResult<NoteUpdateContext> {
    let jobs = state.jobs.read().await;
    let job = jobs.get(&id).ok_or_else(not_found_job)?;
    ensure_job_editable(job)?;
    Ok(NoteUpdateContext {
        midi_tempo: job.midi_tempo,
        soundfont: state.soundfont.clone(),
        timeout_secs: state.config.fluidsynth_timeout_secs,
        wav_path: state.temp_dir.join(format!("{id}.wav")),
    })
}

fn ensure_job_editable(job: &crate::state::Job) -> AppResult<()> {
    if job.result.is_none() {
        return Err(AppError::BadRequest("transcripcion no lista".into()));
    }
    if matches!(job.status, JobStatus::Queued | JobStatus::Running) {
        return Err(AppError::BadRequest("el job está en ejecución".into()));
    }
    Ok(())
}

fn clean_notes(notes: Vec<NoteDto>) -> AppResult<Vec<basic_pitch_midi_io::NoteEvent>> {
    let mut cleaned = Vec::with_capacity(notes.len());
    for note in &notes {
        cleaned.push(clean_note(note)?);
    }
    cleaned.sort_by(|a, b| {
        a.start_time
            .partial_cmp(&b.start_time)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.pitch.cmp(&b.pitch))
    });
    Ok(cleaned)
}

fn clean_note(note: &NoteDto) -> AppResult<basic_pitch_midi_io::NoteEvent> {
    validate_note(note)?;
    Ok(basic_pitch_midi_io::NoteEvent {
        start_time: note.start_time,
        end_time: note.end_time,
        pitch: note.pitch,
        velocity: note.velocity,
        amplitude: normalized_amplitude(note),
        pitch_bend: note.pitch_bend.clone(),
    })
}

fn validate_note(note: &NoteDto) -> AppResult<()> {
    if !(21..=108).contains(&note.pitch) {
        return Err(AppError::BadRequest(format!(
            "pitch fuera de rango: {}",
            note.pitch
        )));
    }
    if note.velocity > 127 {
        return Err(AppError::BadRequest("velocity fuera de rango".into()));
    }
    if !note.start_time.is_finite() || !note.end_time.is_finite() || note.start_time < 0.0 {
        return Err(AppError::BadRequest("tiempos de nota inválidos".into()));
    }
    if note.end_time <= note.start_time {
        return Err(AppError::BadRequest(
            "end_time debe ser mayor que start_time".into(),
        ));
    }
    Ok(())
}

fn normalized_amplitude(note: &NoteDto) -> f32 {
    if note.amplitude.is_finite() && note.amplitude > 0.0 {
        return note.amplitude.clamp(0.0, 1.0);
    }
    (note.velocity as f32 / 127.0).clamp(0.0, 1.0)
}

fn build_midi(notes: &[basic_pitch_midi_io::NoteEvent], midi_tempo: f64) -> AppResult<Vec<u8>> {
    let mut writer = basic_pitch_midi_io::MidiWriter::new();
    writer.tempo = if midi_tempo.is_finite() && midi_tempo > 0.0 {
        midi_tempo
    } else {
        120.0
    };
    writer
        .to_bytes(notes)
        .map_err(|e| AppError::Internal(format!("no se pudo generar MIDI: {e}")))
}

async fn render_updated_audio(
    ctx: &NoteUpdateContext,
    midi_data: &[u8],
) -> AppResult<Result<(), String>> {
    let midi = midi_data.to_vec();
    let soundfont = ctx.soundfont.clone();
    let wav_path = ctx.wav_path.clone();
    let timeout = ctx.timeout_secs;
    tokio::task::spawn_blocking(move || {
        crate::audio::render_midi_to_wav(&midi, &soundfont, &wav_path, timeout)
    })
    .await
    .map_err(|e| AppError::Internal(e.to_string()))
}

async fn apply_note_update(
    state: &AppState,
    id: Uuid,
    cleaned: Vec<basic_pitch_midi_io::NoteEvent>,
    midi_data: Vec<u8>,
    wav_path: std::path::PathBuf,
    render_result: Result<(), String>,
) -> AppResult<()> {
    let mut jobs = state.jobs.write().await;
    let job = jobs.get_mut(&id).ok_or_else(not_found_job)?;
    replace_rendered_audio(job, &wav_path, render_result);
    job.edited_midi = Some(midi_data);
    job.edited_notes = Some(cleaned);
    Ok(())
}

fn replace_rendered_audio(
    job: &mut crate::state::Job,
    wav_path: &std::path::Path,
    render_result: Result<(), String>,
) {
    if let Some(old) = job.rendered_audio.take() {
        if old != wav_path {
            let _ = std::fs::remove_file(old);
        }
    }
    match render_result {
        Ok(()) => {
            job.rendered_audio = Some(wav_path.to_path_buf());
            job.error = None;
        }
        Err(err) => {
            let _ = std::fs::remove_file(wav_path);
            job.rendered_audio = None;
            job.error = Some(format!("notas guardadas; audio no disponible: {err}"));
        }
    }
}
