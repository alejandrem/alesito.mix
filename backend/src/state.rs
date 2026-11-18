use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;

use basic_pitch_transcription::{Transcriber, TranscriptionResult};
use tokio::sync::RwLock;
use uuid::Uuid;

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
}

#[derive(Clone)]
pub struct AppState {
    pub transcriber: Arc<Transcriber>,
    pub jobs: Arc<RwLock<HashMap<Uuid, Job>>>,
    pub temp_dir: PathBuf,
}

impl AppState {
    pub fn new(transcriber: Transcriber, temp_dir: PathBuf) -> Self {
        Self {
            transcriber: Arc::new(transcriber),
            jobs: Arc::new(RwLock::new(HashMap::new())),
            temp_dir,
        }
    }
}