use basic_pitch_midi_io::NoteEvent;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Clone, Copy, Debug)]
pub struct TranscriptionOptions {
    pub onset_threshold: f64,
    pub frame_threshold: f64,
    pub minimum_note_length_ms: f64,
    pub min_freq: Option<f64>,
    pub max_freq: Option<f64>,
    pub melodia_trick: bool,
    pub midi_tempo: f64,
    pub multiple_pitch_bends: bool,
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

#[derive(Debug, Default, Deserialize)]
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
    pub fn apply(self, mut opts: TranscriptionOptions) -> TranscriptionOptions {
        if let Some(v) = self.onset_threshold {
            opts.onset_threshold = v;
        }
        if let Some(v) = self.frame_threshold {
            opts.frame_threshold = v;
        }
        if let Some(v) = self.minimum_note_length_ms {
            opts.minimum_note_length_ms = v;
        }
        if let Some(v) = self.min_freq {
            opts.min_freq = Some(v);
        }
        if let Some(v) = self.max_freq {
            opts.max_freq = Some(v);
        }
        if let Some(v) = self.melodia_trick {
            opts.melodia_trick = parse_bool(&v);
        }
        if let Some(v) = self.midi_tempo {
            opts.midi_tempo = v;
        }
        if let Some(v) = self.multiple_pitch_bends {
            opts.multiple_pitch_bends = parse_bool(&v);
        }
        opts
    }
}

fn parse_bool(value: &str) -> bool {
    value == "true" || value == "1"
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

pub fn note_to_dto(note: &NoteEvent) -> NoteDto {
    NoteDto {
        start_time: note.start_time,
        end_time: note.end_time,
        pitch: note.pitch,
        velocity: note.velocity,
        amplitude: note.amplitude,
        pitch_bend: note.pitch_bend.clone(),
    }
}
