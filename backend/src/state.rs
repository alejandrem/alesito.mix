use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;

use basic_pitch_transcription::{Transcriber, TranscriptionResult};
use tokio::sync::{RwLock, Semaphore};
use uuid::Uuid;

/// Configuración de límites de recursos del servidor.
#[derive(Clone, Debug)]
pub struct ServerConfig {
    /// Máximo de jobs activos en memoria (default 50).
    pub max_jobs: usize,
    /// Tamaño máximo de archivo de audio en bytes (default 100 MB).
    pub max_audio_size_bytes: u64,
    /// Timeout para fluidsynth en segundos (default 120s).
    pub fluidsynth_timeout_secs: u64,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            max_jobs: std::env::var("MAX_JOBS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(50),
            max_audio_size_bytes: std::env::var("MAX_AUDIO_SIZE_MB")
                .ok()
                .and_then(|v| v.parse::<u64>().ok())
                .map(|mb| mb * 1024 * 1024)
                .unwrap_or(100 * 1024 * 1024),
            fluidsynth_timeout_secs: std::env::var("FLUIDSYNTH_TIMEOUT_SECS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(120),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum JobStatus {
    Queued,
    Running,
    Done,
    Failed,
}

impl JobStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            JobStatus::Queued => "queued",
            JobStatus::Running => "running",
            JobStatus::Done => "done",
            JobStatus::Failed => "failed",
        }
    }
}

#[derive(Clone)]
pub struct Job {
    pub id: Uuid,
    pub status: JobStatus,
    #[allow(dead_code)]
    pub audio_path: Option<PathBuf>,
    pub result: Option<TranscriptionResult>,
    pub error: Option<String>,
    pub rendered_audio: Option<PathBuf>,
    pub created_at: std::time::Instant,
}

#[derive(Clone)]
pub struct AppState {
    pub transcriber: Arc<Transcriber>,
    pub jobs: Arc<RwLock<HashMap<Uuid, Job>>>,
    pub audio_render_slots: Arc<Semaphore>,
    pub temp_dir: PathBuf,
    pub soundfont: PathBuf,
    pub config: ServerConfig,
}

impl AppState {
    pub fn new(transcriber: Transcriber, temp_dir: PathBuf, soundfont: PathBuf) -> Self {
        Self {
            transcriber: Arc::new(transcriber),
            jobs: Arc::new(RwLock::new(HashMap::new())),
            audio_render_slots: Arc::new(Semaphore::new(2)),
            temp_dir,
            soundfont,
            config: ServerConfig::default(),
        }
    }
}
