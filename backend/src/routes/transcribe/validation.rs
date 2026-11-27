use std::path::Path;

use symphonia::core::errors::Error as SymphoniaError;
use symphonia::core::formats::FormatOptions;
use symphonia::core::io::MediaSourceStream;
use symphonia::core::meta::MetadataOptions;
use symphonia::core::probe::Hint;

use crate::error::{AppError, AppResult};

use super::dto::TranscriptionOptions;

pub fn validate_options(opts: &TranscriptionOptions) -> AppResult<()> {
    validate_threshold("onset_threshold", opts.onset_threshold)?;
    validate_threshold("frame_threshold", opts.frame_threshold)?;
    validate_note_length(opts.minimum_note_length_ms)?;
    validate_freq("min_freq", opts.min_freq)?;
    validate_freq("max_freq", opts.max_freq)?;
    validate_freq_range(opts.min_freq, opts.max_freq)?;
    validate_tempo(opts.midi_tempo)
}

fn validate_threshold(name: &str, value: f64) -> AppResult<()> {
    if (0.0..=1.0).contains(&value) {
        return Ok(());
    }
    Err(AppError::BadRequest(format!(
        "{name} fuera de rango (0.0-1.0)"
    )))
}

fn validate_note_length(value: f64) -> AppResult<()> {
    if value.is_finite() && value > 0.0 && value <= 2000.0 {
        return Ok(());
    }
    Err(AppError::BadRequest(
        "minimum_note_length_ms fuera de rango (0-2000)".into(),
    ))
}

fn validate_freq(name: &str, value: Option<f64>) -> AppResult<()> {
    let Some(value) = value else {
        return Ok(());
    };
    if value.is_finite() && value > 0.0 {
        return Ok(());
    }
    Err(AppError::BadRequest(format!("{name} invalido")))
}

fn validate_freq_range(min_freq: Option<f64>, max_freq: Option<f64>) -> AppResult<()> {
    let (Some(min_f), Some(max_f)) = (min_freq, max_freq) else {
        return Ok(());
    };
    if min_f < max_f {
        return Ok(());
    }
    Err(AppError::BadRequest(
        "min_freq debe ser menor que max_freq".into(),
    ))
}

fn validate_tempo(value: f64) -> AppResult<()> {
    if value.is_finite() && value > 0.0 {
        return Ok(());
    }
    Err(AppError::BadRequest("midi_tempo invalido".into()))
}

pub fn audio_duration_seconds(path: &Path) -> Result<f64, String> {
    let mut format = open_audio_format(path)?;
    let track = format
        .default_track()
        .ok_or_else(|| "el audio no contiene pistas".to_string())?;
    let track_id = track.id;
    let sample_rate = track_sample_rate(track)?;
    let frame_count = count_track_frames(&mut *format, track_id)?;
    Ok(frame_count as f64 / sample_rate as f64)
}

fn open_audio_format(
    path: &Path,
) -> Result<Box<dyn symphonia::core::formats::FormatReader>, String> {
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
    Ok(probed.format)
}

fn track_sample_rate(track: &symphonia::core::formats::Track) -> Result<u32, String> {
    let sample_rate = track
        .codec_params
        .sample_rate
        .ok_or_else(|| "no se pudo determinar la frecuencia del audio".to_string())?;
    if sample_rate == 0 {
        return Err("frecuencia de audio inválida".into());
    }
    Ok(sample_rate)
}

fn count_track_frames(
    format: &mut dyn symphonia::core::formats::FormatReader,
    track_id: u32,
) -> Result<u64, String> {
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
    Ok(frame_count)
}

pub fn is_audio_duration_allowed(duration_seconds: f64, max_duration_seconds: u64) -> bool {
    duration_seconds.is_finite() && duration_seconds <= max_duration_seconds as f64
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
