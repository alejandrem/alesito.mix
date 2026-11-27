use axum::body::Body;
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{Multipart, Path, Query, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde::{Deserialize, Serialize};
use serde_json::json;
use uuid::Uuid;

use crate::error::{AppError, AppResult};
use crate::state::{AppState, Job, JobStatus, ProgressEvent};

#[derive(Clone, Copy, Debug)]
struct TranscriptionOptions {
    onset_threshold: f64,
    frame_threshold: f64,
    minimum_note_length_ms: f64,
    min_freq: Option<f64>,
    max_freq: Option<f64>,
    melodia_trick: bool,
    midi_tempo: f64,
    multiple_pitch_bends: bool,
}

impl Default for TranscriptionOptions {
    fn default() -> Self {
        Self {
            onset_threshold: 0.5,
            frame_threshold: 0.3,
            minimum_note_length_ms: 127.7,
            min_freq: None,
            max_freq: None,
            melodia_trick: true,
            midi_tempo: 120.0,
            multiple_pitch_bends: false,
        }
    }
}

#[derive(Debug, Default, serde::Deserialize)]
pub struct TranscriptionQuery {
    pub onset_threshold: Option<f64>,
    pub frame_threshold: Option<f64>,
    pub minimum_note_length_ms: Option<f64>,
    pub min_freq: Option<f64>,
    pub max_freq: Option<f64>,
    pub melodia_trick: Option<String>,
    pub midi_tempo: Option<f64>,
    pub multiple_pitch_bends: Option<String>,
}

impl TranscriptionQuery {
    fn apply(self, mut opts: TranscriptionOptions) -> TranscriptionOptions {
        if let Some(v) = self.onset_threshold { opts.onset_threshold = v; }
        if let Some(v) = self.frame_threshold { opts.frame_threshold = v; }
        if let Some(v) = self.minimum_note_length_ms { opts.minimum_note_length_ms = v; }
        if let Some(v) = self.min_freq { opts.min_freq = Some(v); }
        if let Some(v) = self.max_freq { opts.max_freq = Some(v); }
        if let Some(v) = self.melodia_trick { opts.melodia_trick = v == "true" || v == "1"; }
        if let Some(v) = self.midi_tempo { opts.midi_tempo = v; }
        if let Some(v) = self.multiple_pitch_bends { opts.multiple_pitch_bends = v == "true" || v == "1"; }
        opts
    }
}

async fn ensure_job_capacity(state: &AppState) -> AppResult<()> {
    let jobs = state.jobs.read().await;
    if jobs.len() >= state.config.max_jobs {
        return Err(AppError::TooManyJobs(format!(
            "servidor sobrecargado (maximo {} jobs activos)",
            state.config.max_jobs
        )));
    }
    Ok(())
}

fn audio_duration_seconds(path: &std::path::Path) -> Result<f64, String> {
    use symphonia::core::errors::Error as SymphoniaError;
    use symphonia::core::formats::FormatOptions;
    use symphonia::core::io::MediaSourceStream;
    use symphonia::core::meta::MetadataOptions;
    use symphonia::core::probe::Hint;

    let file = std::fs::File::open(path).map_err(|error| error.to_string())?;
    let source = MediaSourceStream::new(Box::new(file), Default::default());
    let probed = symphonia::default::get_probe()
        .format(
            &Hint::new(),
            source,
            &FormatOptions::default(),
            &MetadataOptions::default(),
        )
        .map_err(|error| error.to_string())?;
    let mut format = probed.format;
    let track = format
        .default_track()
        .ok_or_else(|| "el audio no contiene pistas".to_string())?;
    let track_id = track.id;
    let sample_rate = track
        .codec_params
        .sample_rate
        .ok_or_else(|| "no se pudo determinar la frecuencia del audio".to_string())?;
    if sample_rate == 0 {
        return Err("frecuencia de audio inválida".into());
    }
    let mut frame_count = 0u64;

    loop {
        let packet = match format.next_packet() {
            Ok(packet) => packet,
            Err(SymphoniaError::IoError(error))
                if error.kind() == std::io::ErrorKind::UnexpectedEof =>
            {
                break;
            }
            Err(error) => return Err(error.to_string()),
        };
        if packet.track_id() == track_id {
            frame_count = frame_count.saturating_add(packet.dur());
        }
    }

    if frame_count == 0 {
        return Err("el audio no contiene frames decodificables".into());
    }
    Ok(frame_count as f64 / sample_rate as f64)
}

fn is_audio_duration_allowed(duration_seconds: f64, max_duration_seconds: u64) -> bool {
    duration_seconds.is_finite() && duration_seconds <= max_duration_seconds as f64
}

/// Borra los archivos temporales de un job (audio original + WAV renderizado).
fn cleanup_job_files(job: &Job) {
    if let Some(ref path) = job.audio_path {
        let _ = std::fs::remove_file(path);
    }
    if let Some(ref path) = job.rendered_audio {
        let _ = std::fs::remove_file(path);
    }
}

#[derive(Serialize)]
pub struct JobResponse {
    pub id: Uuid,
    pub status: &'static str,
    pub notes_count: Option<usize>,
    pub duration_seconds: Option<f64>,
    pub error: Option<String>,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct NoteDto {
    pub start_time: f64,
    pub end_time: f64,
    pub pitch: u8,
    pub velocity: u8,
    #[serde(default)]
    pub amplitude: f32,
    #[serde(default)]
    pub pitch_bend: Option<Vec<i16>>,
}

pub async fn create_transcription(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> AppResult<Json<serde_json::Value>> {
    ensure_job_capacity(&state).await?;

    // Leer el archivo de audio del multipart, streaming directo a disco.
    let mut options = TranscriptionOptions::default();
    let mut audio_path: Option<std::path::PathBuf> = None;

    let job_id = Uuid::new_v4();
    let max_size = state.config.max_audio_size_bytes;

    while let Some(mut field) = multipart
        .next_field()
        .await
        .map_err(|e| AppError::BadRequest(e.to_string()))?
    {
        match field.name() {
            Some("audio") => {
                let filename = field.file_name().unwrap_or("audio").to_string();
                let ext = std::path::Path::new(&filename)
                    .extension()
                    .and_then(|e| e.to_str())
                    .unwrap_or("wav");
                let path = state.temp_dir.join(format!("{job_id}.{ext}"));

                // Streaming directo a disco con limite de tamaño.
                let mut file = tokio::fs::File::create(&path)
                    .await
                    .map_err(|e| AppError::Internal(e.to_string()))?;
                let mut total_size: u64 = 0;

                use futures::StreamExt;
                use tokio::io::AsyncWriteExt;
                while let Some(chunk) = field.next().await {
                    let chunk = chunk.map_err(|e| AppError::BadRequest(e.to_string()))?;
                    total_size += chunk.len() as u64;
                    if total_size > max_size {
                        // Limite excedido: borrar el archivo parcial.
                        let _ = tokio::fs::remove_file(&path).await;
                        return Err(AppError::BadRequest(format!(
                            "audio demasiado grande (maximo {} MB)",
                            max_size / 1024 / 1024
                        )));
                    }
                    file.write_all(&chunk)
                        .await
                        .map_err(|e| AppError::Internal(e.to_string()))?;
                }
                audio_path = Some(path);
            }
            Some("onset_threshold") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                options.onset_threshold = v.parse().map_err(|_| AppError::BadRequest("onset_threshold invalido".into()))?;
            }
            Some("frame_threshold") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                options.frame_threshold = v.parse().map_err(|_| AppError::BadRequest("frame_threshold invalido".into()))?;
            }
            Some("minimum_note_length_ms") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                options.minimum_note_length_ms = v.parse().map_err(|_| AppError::BadRequest("minimum_note_length_ms invalido".into()))?;
            }
            Some("min_freq") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                let parsed: f64 = v.parse().map_err(|_| AppError::BadRequest("min_freq invalido".into()))?;
                options.min_freq = Some(parsed);
            }
            Some("max_freq") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                let parsed: f64 = v.parse().map_err(|_| AppError::BadRequest("max_freq invalido".into()))?;
                options.max_freq = Some(parsed);
            }
            Some("melodia_trick") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                options.melodia_trick = v == "true" || v == "1";
            }
            Some("midi_tempo") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                options.midi_tempo = v.parse().map_err(|_| AppError::BadRequest("midi_tempo invalido".into()))?;
            }
            Some("multiple_pitch_bends") => {
                let v = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                options.multiple_pitch_bends = v == "true" || v == "1";
            }
            _ => {}
        }
    }

    let audio_path =
        audio_path.ok_or_else(|| AppError::BadRequest("falta el campo 'audio'".into()))?;

    start_transcription(state, job_id, audio_path, options).await
}

pub async fn create_transcription_audio(
    State(state): State<AppState>,
    Query(query): Query<TranscriptionQuery>,
    body: Body,
) -> AppResult<Json<serde_json::Value>> {
    ensure_job_capacity(&state).await?;

    let upload_started = std::time::Instant::now();
    let job_id = Uuid::new_v4();
    let audio_path = state.temp_dir.join(format!("{job_id}.mp3"));
    let mut file = tokio::fs::File::create(&audio_path)
        .await
        .map_err(|error| AppError::Internal(error.to_string()))?;
    let mut total_size = 0u64;
    let max_size = state.config.max_audio_size_bytes;

    use futures::StreamExt;
    use tokio::io::AsyncWriteExt;
    let mut stream = body.into_data_stream();
    while let Some(chunk) = stream.next().await {
        let chunk = match chunk {
            Ok(chunk) => chunk,
            Err(error) => {
                let _ = tokio::fs::remove_file(&audio_path).await;
                return Err(AppError::BadRequest(error.to_string()));
            }
        };
        total_size += chunk.len() as u64;
        if total_size > max_size {
            let _ = tokio::fs::remove_file(&audio_path).await;
            return Err(AppError::BadRequest(format!(
                "audio demasiado grande (maximo {} MB)",
                max_size / 1024 / 1024
            )));
        }
        if let Err(error) = file.write_all(&chunk).await {
            let _ = tokio::fs::remove_file(&audio_path).await;
            return Err(AppError::Internal(error.to_string()));
        }
    }
    drop(file);
    tracing::info!(
        %job_id,
        bytes = total_size,
        upload_ms = upload_started.elapsed().as_millis(),
        "audio recibido"
    );

    let options = query.apply(TranscriptionOptions::default());
    start_transcription(state, job_id, audio_path, options).await
}

async fn start_transcription(
    state: AppState,
    job_id: Uuid,
    audio_path: std::path::PathBuf,
    options: TranscriptionOptions,
) -> AppResult<Json<serde_json::Value>> {
    if !(0.0..=1.0).contains(&options.onset_threshold) {
        let _ = tokio::fs::remove_file(&audio_path).await;
        return Err(AppError::BadRequest("onset_threshold fuera de rango (0.0-1.0)".into()));
    }
    if !(0.0..=1.0).contains(&options.frame_threshold) {
        let _ = tokio::fs::remove_file(&audio_path).await;
        return Err(AppError::BadRequest("frame_threshold fuera de rango (0.0-1.0)".into()));
    }
    if !options.minimum_note_length_ms.is_finite() || options.minimum_note_length_ms <= 0.0 || options.minimum_note_length_ms > 2000.0 {
        let _ = tokio::fs::remove_file(&audio_path).await;
        return Err(AppError::BadRequest("minimum_note_length_ms fuera de rango (0-2000)".into()));
    }
    if let Some(min_freq) = options.min_freq {
        if !min_freq.is_finite() || min_freq <= 0.0 { let _ = tokio::fs::remove_file(&audio_path).await; return Err(AppError::BadRequest("min_freq invalido".into())); }
    }
    if let Some(max_freq) = options.max_freq {
        if !max_freq.is_finite() || max_freq <= 0.0 { let _ = tokio::fs::remove_file(&audio_path).await; return Err(AppError::BadRequest("max_freq invalido".into())); }
    }
    if let (Some(min_freq), Some(max_freq)) = (options.min_freq, options.max_freq) {
        if min_freq >= max_freq { let _ = tokio::fs::remove_file(&audio_path).await; return Err(AppError::BadRequest("min_freq debe ser menor que max_freq".into())); }
    }
    if !options.midi_tempo.is_finite() || options.midi_tempo <= 0.0 {
        let _ = tokio::fs::remove_file(&audio_path).await;
        return Err(AppError::BadRequest("midi_tempo invalido".into()));
    }

    let validation_started = std::time::Instant::now();
    let duration_path = audio_path.clone();
    let duration =
        match tokio::task::spawn_blocking(move || audio_duration_seconds(&duration_path)).await {
            Ok(Ok(duration)) => duration,
            Ok(Err(error)) => {
                let _ = tokio::fs::remove_file(&audio_path).await;
                return Err(AppError::BadRequest(format!(
                    "audio inválido o formato no soportado: {error}"
                )));
            }
            Err(error) => {
                let _ = tokio::fs::remove_file(&audio_path).await;
                return Err(AppError::Internal(error.to_string()));
            }
        };
    if !is_audio_duration_allowed(duration, state.config.max_audio_duration_secs) {
        let _ = tokio::fs::remove_file(&audio_path).await;
        return Err(AppError::BadRequest(format!(
            "audio demasiado largo (máximo {} minutos)",
            state.config.max_audio_duration_secs / 60
        )));
    }
    tracing::info!(
        %job_id,
        audio_duration_seconds = duration,
        validation_ms = validation_started.elapsed().as_millis(),
        "validación de audio completada"
    );

    let (progress_tx, _) = tokio::sync::broadcast::channel(16);
    let _ = progress_tx.send(ProgressEvent::stage("queued", 0));

    {
        let mut jobs = state.jobs.write().await;
        jobs.insert(
            job_id,
            Job {
                id: job_id,
                status: JobStatus::Queued,
                audio_path: Some(audio_path.clone()),
                result: None,
                edited_notes: None,
                edited_midi: None,
                midi_tempo: options.midi_tempo,
                error: None,
                rendered_audio: None,
                created_at: std::time::Instant::now(),
                progress_tx: progress_tx.clone(),
            },
        );
    }

    let state_clone = state.clone();
    let timeout_secs = state.config.fluidsynth_timeout_secs;
    let progress_tx_task = progress_tx.clone();
    tokio::spawn(async move {
        {
            let mut jobs = state_clone.jobs.write().await;
            if let Some(job) = jobs.get_mut(&job_id) {
                job.status = JobStatus::Running;
                let _ = job.progress_tx.send(ProgressEvent::stage("transcribing", 10));
            }
        }

        let mut transcriber = (*state_clone.transcriber).clone();
        transcriber.config.note_detection.onset_threshold = options.onset_threshold;
        transcriber.config.note_detection.frame_threshold = options.frame_threshold;
        transcriber.config.note_detection.minimum_note_length_ms = options.minimum_note_length_ms;
        transcriber.config.note_detection.min_freq = options.min_freq;
        transcriber.config.note_detection.max_freq = options.max_freq;
        transcriber.config.note_detection.melodia_trick = options.melodia_trick;
        transcriber.config.midi_tempo = options.midi_tempo;
        transcriber.config.multiple_pitch_bends = options.multiple_pitch_bends;

        let path = audio_path.clone();
        let transcription_started = std::time::Instant::now();
        let outcome = tokio::task::spawn_blocking(move || transcriber.transcribe(&path)).await;
        let transcription_ms = transcription_started.elapsed().as_millis();

        let mut jobs = state_clone.jobs.write().await;
        if let Some(job) = jobs.get_mut(&job_id) {
            match outcome {
                Ok(Ok(result)) => {
                    tracing::info!(
                        %job_id,
                        transcription_ms,
                        notes = result.notes.len(),
                        "transcripción Rust completada"
                    );
                    let wav_path = state_clone.temp_dir.join(format!("{job_id}.wav"));
                    let render_started = std::time::Instant::now();
                    match crate::audio::render_midi_to_wav(
                        &result.midi_data,
                        &state_clone.soundfont,
                        &wav_path,
                        timeout_secs,
                    ) {
                        Ok(()) => {
                            tracing::info!(
                                %job_id,
                                render_ms = render_started.elapsed().as_millis(),
                                "renderizado WAV completado"
                            );
                            job.rendered_audio = Some(wav_path)
                        }
                        Err(error) => {
                            tracing::warn!(
                                %job_id,
                                render_ms = render_started.elapsed().as_millis(),
                                %error,
                                "falló el renderizado WAV"
                            );
                            let _ = std::fs::remove_file(&wav_path);
                            job.error =
                                Some(format!("transcripción lista; audio no disponible: {error}"));
                        }
                    }
                    let notes = result.notes.len();
                    let duration = result.duration_seconds;
                    job.result = Some(result);
                    job.status = JobStatus::Done;
                    let _ = progress_tx_task.send(ProgressEvent::Done { notes, duration });
                }
                Ok(Err(error)) => {
                    tracing::warn!(%job_id, transcription_ms, %error, "falló la transcripción Rust");
                    let message = error.to_string();
                    let _ = progress_tx_task.send(ProgressEvent::Error { message: message.clone() });
                    job.status = JobStatus::Failed;
                    job.error = Some(message);
                    cleanup_job_files(job);
                    job.audio_path = None;
                    job.rendered_audio = None;
                }
                Err(error) => {
                    tracing::warn!(%job_id, transcription_ms, %error, "se canceló la tarea de transcripción");
                    let message = format!("tarea cancelada: {error}");
                    let _ = progress_tx_task.send(ProgressEvent::Error { message: message.clone() });
                    job.status = JobStatus::Failed;
                    job.error = Some(message);
                    cleanup_job_files(job);
                    job.audio_path = None;
                    job.rendered_audio = None;
                }
            }
        }
    });

    Ok(Json(json!({ "job_id": job_id })))
}

pub async fn retranscribe_job(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Query(query): Query<TranscriptionQuery>,
) -> AppResult<Json<serde_json::Value>> {
    ensure_job_capacity(&state).await?;
    let (audio_path, prev_rendered) = {
        let jobs = state.jobs.read().await;
        let job = jobs.get(&id).ok_or_else(|| AppError::NotFound("job no encontrado".into()))?;
        if matches!(job.status, JobStatus::Queued | JobStatus::Running) {
            return Err(AppError::BadRequest("el job ya está en ejecución".into()));
        }
        let audio = job.audio_path.clone().ok_or_else(|| AppError::BadRequest("el audio original ya no está disponible; vuelve a subir el archivo".into()))?;
        (audio, job.rendered_audio.clone())
    };
    if let Some(p) = prev_rendered { let _ = tokio::fs::remove_file(p).await; }

    let options = query.apply(TranscriptionOptions::default());

    // Reset job state and re-run with new options
    let (progress_tx, _) = tokio::sync::broadcast::channel(16);
    let _ = progress_tx.send(ProgressEvent::stage("queued", 0));
    {
        let mut jobs = state.jobs.write().await;
        if let Some(job) = jobs.get_mut(&id) {
            job.status = JobStatus::Queued;
            job.result = None;
            job.edited_notes = None;
            job.edited_midi = None;
            job.midi_tempo = options.midi_tempo;
            job.error = None;
            job.rendered_audio = None;
            job.progress_tx = progress_tx.clone();
        }
    }
    // Reuse start_transcription logic by spawning directly; easier to call a helper.
    // We'll inline: create a new job id? No, keep same id for simplicity.
    start_transcription_existing(state, id, audio_path, options, progress_tx).await
}

async fn start_transcription_existing(
    state: AppState,
    job_id: Uuid,
    audio_path: std::path::PathBuf,
    options: TranscriptionOptions,
    progress_tx: tokio::sync::broadcast::Sender<ProgressEvent>,
) -> AppResult<Json<serde_json::Value>> {
    // validate
    if !(0.0..=1.0).contains(&options.onset_threshold) { return Err(AppError::BadRequest("onset_threshold fuera de rango (0.0-1.0)".into())); }
    if !(0.0..=1.0).contains(&options.frame_threshold) { return Err(AppError::BadRequest("frame_threshold fuera de rango (0.0-1.0)".into())); }
    if !options.minimum_note_length_ms.is_finite() || options.minimum_note_length_ms <= 0.0 || options.minimum_note_length_ms > 2000.0 { return Err(AppError::BadRequest("minimum_note_length_ms fuera de rango (0-2000)".into())); }
    if let (Some(min_f), Some(max_f)) = (options.min_freq, options.max_freq) { if min_f >= max_f { return Err(AppError::BadRequest("min_freq debe ser menor que max_freq".into())); } }
    if !options.midi_tempo.is_finite() || options.midi_tempo <= 0.0 { return Err(AppError::BadRequest("midi_tempo invalido".into())); }

    let state_clone = state.clone();
    let timeout_secs = state.config.fluidsynth_timeout_secs;
    let progress_tx_task = progress_tx.clone();
    tokio::spawn(async move {
        {
            let mut jobs = state_clone.jobs.write().await;
            if let Some(job) = jobs.get_mut(&job_id) { job.status = JobStatus::Running; let _ = job.progress_tx.send(ProgressEvent::stage("transcribing", 10)); }
        }
        let mut transcriber = (*state_clone.transcriber).clone();
        transcriber.config.note_detection.onset_threshold = options.onset_threshold;
        transcriber.config.note_detection.frame_threshold = options.frame_threshold;
        transcriber.config.note_detection.minimum_note_length_ms = options.minimum_note_length_ms;
        transcriber.config.note_detection.min_freq = options.min_freq;
        transcriber.config.note_detection.max_freq = options.max_freq;
        transcriber.config.note_detection.melodia_trick = options.melodia_trick;
        transcriber.config.midi_tempo = options.midi_tempo;
        transcriber.config.multiple_pitch_bends = options.multiple_pitch_bends;

        let path = audio_path.clone();
        let outcome = tokio::task::spawn_blocking(move || transcriber.transcribe(&path)).await;
        let mut jobs = state_clone.jobs.write().await;
        if let Some(job) = jobs.get_mut(&job_id) {
            match outcome {
                Ok(Ok(result)) => {
                    let wav_path = state_clone.temp_dir.join(format!("{job_id}.wav"));
                    match crate::audio::render_midi_to_wav(&result.midi_data, &state_clone.soundfont, &wav_path, timeout_secs) {
                        Ok(()) => { job.rendered_audio = Some(wav_path); }
                        Err(error) => { let _ = std::fs::remove_file(&wav_path); job.error = Some(format!("transcripción lista; audio no disponible: {error}")); }
                    }
                    let notes = result.notes.len(); let duration = result.duration_seconds;
                    job.result = Some(result); job.status = JobStatus::Done;
                    let _ = progress_tx_task.send(ProgressEvent::Done { notes, duration });
                }
                Ok(Err(error)) => { let message = error.to_string(); let _ = progress_tx_task.send(ProgressEvent::Error { message: message.clone() }); job.status = JobStatus::Failed; job.error = Some(message); }
                Err(error) => { let message = format!("tarea cancelada: {error}"); let _ = progress_tx_task.send(ProgressEvent::Error { message: message.clone() }); job.status = JobStatus::Failed; job.error = Some(message); }
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
    let job = jobs
        .get(&id)
        .ok_or_else(|| AppError::NotFound("job no encontrado".into()))?;

    let (count, dur) = if let Some(edited) = &job.edited_notes {
        let duration = edited
            .iter()
            .map(|n| n.end_time)
            .fold(
                job.result.as_ref().map(|r| r.duration_seconds).unwrap_or(0.0),
                f64::max,
            );
        (Some(edited.len()), Some(duration))
    } else {
        match &job.result {
            Some(r) => (Some(r.notes.len()), Some(r.duration_seconds)),
            None => (None, None),
        }
    };

    Ok(Json(JobResponse {
        id: job.id,
        status: job.status.as_str(),
        notes_count: count,
        duration_seconds: dur,
        error: job.error.clone(),
    }))
}

fn note_to_dto(n: &basic_pitch_midi_io::NoteEvent) -> NoteDto {
    NoteDto {
        start_time: n.start_time,
        end_time: n.end_time,
        pitch: n.pitch,
        velocity: n.velocity,
        amplitude: n.amplitude,
        pitch_bend: n.pitch_bend.clone(),
    }
}

pub async fn get_notes(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> AppResult<Json<Vec<NoteDto>>> {
    let jobs = state.jobs.read().await;
    let job = jobs
        .get(&id)
        .ok_or_else(|| AppError::NotFound("job no encontrado".into()))?;

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
    let job = jobs
        .get(&id)
        .ok_or_else(|| AppError::NotFound("job no encontrado".into()))?;

    let midi = if let Some(edited) = &job.edited_midi {
        edited.clone()
    } else {
        let result = job
            .result
            .as_ref()
            .ok_or_else(|| AppError::BadRequest("transcripcion no lista".into()))?;
        result.midi_data.clone()
    };

    Ok((
        StatusCode::OK,
        [("content-type", "audio/midi")],
        midi,
    ))
}

pub async fn update_notes(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(notes): Json<Vec<NoteDto>>,
) -> AppResult<Json<Vec<NoteDto>>> {
    let (midi_tempo, soundfont, timeout_secs, temp_dir) = {
        let jobs = state.jobs.read().await;
        let job = jobs
            .get(&id)
            .ok_or_else(|| AppError::NotFound("job no encontrado".into()))?;
        if job.result.is_none() {
            return Err(AppError::BadRequest("transcripcion no lista".into()));
        }
        if matches!(job.status, JobStatus::Queued | JobStatus::Running) {
            return Err(AppError::BadRequest("el job está en ejecución".into()));
        }
        (
            job.midi_tempo,
            state.soundfont.clone(),
            state.config.fluidsynth_timeout_secs,
            state.temp_dir.clone(),
        )
    };

    let mut cleaned: Vec<basic_pitch_midi_io::NoteEvent> = Vec::with_capacity(notes.len());
    for n in &notes {
        if !(21..=108).contains(&n.pitch) {
            return Err(AppError::BadRequest(format!("pitch fuera de rango: {}", n.pitch)));
        }
        if n.velocity > 127 {
            return Err(AppError::BadRequest("velocity fuera de rango".into()));
        }
        if !n.start_time.is_finite() || !n.end_time.is_finite() || n.start_time < 0.0 {
            return Err(AppError::BadRequest("tiempos de nota inválidos".into()));
        }
        if n.end_time <= n.start_time {
            return Err(AppError::BadRequest("end_time debe ser mayor que start_time".into()));
        }
        let amplitude = if n.amplitude.is_finite() && n.amplitude > 0.0 {
            n.amplitude.clamp(0.0, 1.0)
        } else {
            (n.velocity as f32 / 127.0).clamp(0.0, 1.0)
        };
        cleaned.push(basic_pitch_midi_io::NoteEvent {
            start_time: n.start_time,
            end_time: n.end_time,
            pitch: n.pitch,
            velocity: n.velocity,
            amplitude,
            pitch_bend: n.pitch_bend.clone(),
        });
    }

    cleaned.sort_by(|a, b| {
        a.start_time
            .partial_cmp(&b.start_time)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.pitch.cmp(&b.pitch))
    });

    let mut writer = basic_pitch_midi_io::MidiWriter::new();
    writer.tempo = if midi_tempo.is_finite() && midi_tempo > 0.0 { midi_tempo } else { 120.0 };
    let midi_data = writer
        .to_bytes(&cleaned)
        .map_err(|e| AppError::Internal(format!("no se pudo generar MIDI: {e}")))?;

    let wav_path = temp_dir.join(format!("{}.wav", id));
    let midi_for_render = midi_data.clone();
    let soundfont_for_render = soundfont.clone();
    let wav_for_render = wav_path.clone();
    let render_result = tokio::task::spawn_blocking(move || {
        crate::audio::render_midi_to_wav(&midi_for_render, &soundfont_for_render, &wav_for_render, timeout_secs)
    })
    .await
    .map_err(|e| AppError::Internal(e.to_string()))?;

    let mut jobs = state.jobs.write().await;
    let job = jobs
        .get_mut(&id)
        .ok_or_else(|| AppError::NotFound("job no encontrado".into()))?;

    if let Some(old) = job.rendered_audio.take() {
        if old != wav_path {
            let _ = std::fs::remove_file(old);
        }
    }

    match render_result {
        Ok(()) => {
            job.rendered_audio = Some(wav_path);
            job.error = None;
        }
        Err(err) => {
            let _ = std::fs::remove_file(&wav_path);
            job.rendered_audio = None;
            job.error = Some(format!("notas guardadas; audio no disponible: {err}"));
        }
    }

    job.edited_midi = Some(midi_data);
    job.edited_notes = Some(cleaned.clone());

    Ok(Json(cleaned.iter().map(note_to_dto).collect()))
}

pub async fn get_audio(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> AppResult<impl IntoResponse> {
    let jobs = state.jobs.read().await;
    let job = jobs
        .get(&id)
        .ok_or_else(|| AppError::NotFound("job no encontrado".into()))?;
    let path = job
        .rendered_audio
        .clone()
        .ok_or_else(|| AppError::BadRequest("audio no listo".into()))?;
    drop(jobs);

    let bytes = tokio::fs::read(&path)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;

    Ok((StatusCode::OK, [("content-type", "audio/wav")], bytes))
}

pub async fn ws_job(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_ws_job(socket, state, id))
}

async fn handle_ws_job(mut socket: WebSocket, state: AppState, id: Uuid) {
    let (mut rx, current) = {
        let jobs = state.jobs.read().await;
        let Some(job) = jobs.get(&id) else {
            let _ = socket
                .send(Message::Text(
                    serde_json::json!({"type":"error","message":"job no encontrado"}).to_string().into(),
                ))
                .await;
            return;
        };
        let rx = job.progress_tx.subscribe();
        let current = match job.status {
            JobStatus::Queued => ProgressEvent::stage("queued", 0),
            JobStatus::Running => ProgressEvent::stage("transcribing", 10),
            JobStatus::Done => {
                let (notes, duration) = job
                    .result
                    .as_ref()
                    .map(|r| (r.notes.len(), r.duration_seconds))
                    .unwrap_or((0, 0.0));
                ProgressEvent::Done { notes, duration }
            }
            JobStatus::Failed => ProgressEvent::Error {
                message: job.error.clone().unwrap_or_else(|| "error desconocido".into()),
            },
        };
        (rx, current)
    };

    if send_progress(&mut socket, &current).await.is_err() {
        return;
    }
    if matches!(current, ProgressEvent::Done { .. } | ProgressEvent::Error { .. }) {
        return;
    }

    loop {
        tokio::select! {
            msg = socket.recv() => {
                if msg.is_none() { break; }
            }
            evt = rx.recv() => {
                match evt {
                    Ok(event) => {
                        let done = matches!(event, ProgressEvent::Done { .. } | ProgressEvent::Error { .. });
                        if send_progress(&mut socket, &event).await.is_err() { break; }
                        if done { break; }
                    }
                    Err(tokio::sync::broadcast::error::RecvError::Lagged(_)) => continue,
                    Err(tokio::sync::broadcast::error::RecvError::Closed) => break,
                }
            }
        }
    }
}

async fn send_progress(socket: &mut WebSocket, event: &ProgressEvent) -> Result<(), axum::Error> {
    let text = serde_json::to_string(event).unwrap_or_else(|_| "{\"type\":\"error\",\"message\":\"serialization\"}".to_string());
    socket.send(Message::Text(text.into())).await
}

#[cfg(test)]
mod tests {
    use super::{audio_duration_seconds, is_audio_duration_allowed};

    fn write_wav(path: &std::path::Path, frame_count: u32, sample_rate: u32) {
        let data_size = frame_count * 2;
        let mut wav = Vec::with_capacity(44 + data_size as usize);
        wav.extend_from_slice(b"RIFF");
        wav.extend_from_slice(&(36 + data_size).to_le_bytes());
        wav.extend_from_slice(b"WAVEfmt ");
        wav.extend_from_slice(&16u32.to_le_bytes());
        wav.extend_from_slice(&1u16.to_le_bytes());
        wav.extend_from_slice(&1u16.to_le_bytes());
        wav.extend_from_slice(&sample_rate.to_le_bytes());
        wav.extend_from_slice(&(sample_rate * 2).to_le_bytes());
        wav.extend_from_slice(&2u16.to_le_bytes());
        wav.extend_from_slice(&16u16.to_le_bytes());
        wav.extend_from_slice(b"data");
        wav.extend_from_slice(&data_size.to_le_bytes());
        wav.resize(44 + data_size as usize, 0);
        std::fs::write(path, wav).unwrap();
    }

    #[test]
    fn twelve_minute_limit_accepts_boundary_and_rejects_longer_audio() {
        assert!(is_audio_duration_allowed(720.0, 720));
        assert!(!is_audio_duration_allowed(720.001, 720));
        assert!(!is_audio_duration_allowed(f64::INFINITY, 720));
    }

    #[test]
    fn audio_duration_uses_decoded_packet_frames() {
        let path = std::env::temp_dir().join(format!("test-audio-{}.wav", uuid::Uuid::new_v4()));
        write_wav(&path, 8_000, 8_000);

        let duration = audio_duration_seconds(&path).unwrap();
        std::fs::remove_file(path).unwrap();

        assert!((duration - 1.0).abs() < 0.001);
    }

    #[test]
    fn invalid_audio_cannot_be_assigned_a_duration() {
        let path = std::env::temp_dir().join(format!("invalid-audio-{}.mp3", uuid::Uuid::new_v4()));
        std::fs::write(&path, b"not an audio file").unwrap();

        assert!(audio_duration_seconds(&path).is_err());
        std::fs::remove_file(path).unwrap();
    }
}
