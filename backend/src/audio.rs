use std::path::{Path, PathBuf};
use std::process::Command;

pub fn render_midi_to_wav(
    midi: &[u8],
    soundfont: &Path,
    output: &Path,
) -> Result<(), String> {
    let midi_path = output.with_extension("mid");
    std::fs::write(&midi_path, midi).map_err(|e| e.to_string())?;

    let status = Command::new("fluidsynth")
        .args([
            "-ni",
            "-F",
            output.to_str().ok_or("ruta invalida")?,
            "-r",
            "44100",
            "-g",
            "0.7",
            soundfont.to_str().ok_or("soundfont invalido")?,
            midi_path.to_str().ok_or("midi invalido")?,
        ])
        .status()
        .map_err(|e| format!("no se pudo ejecutar fluidsynth: {e}"))?;

    let _ = std::fs::remove_file(&midi_path);

    if !status.success() {
        return Err(format!("fluidsynth fallo con codigo {:?}", status.code()));
    }
    if !output.exists() {
        return Err("fluidsynth no genero el WAV".into());
    }
    Ok(())
}

pub fn default_soundfont() -> PathBuf {
    std::env::var("SOUNDFONT_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("../frontend/FluidR3_GM.sf2"))
}