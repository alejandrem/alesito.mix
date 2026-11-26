use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::time::Duration;

/// Ejecuta fluidsynth con timeout. Si el proceso no termina a tiempo, se mata.
pub fn render_midi_to_wav(
    midi: &[u8],
    soundfont: &Path,
    output: &Path,
    timeout_secs: u64,
) -> Result<(), String> {
    let midi_path = output.with_extension("mid");
    std::fs::write(&midi_path, midi).map_err(|e| e.to_string())?;

    let result = render_midi_file_to_wav(&midi_path, soundfont, output, timeout_secs);
    let _ = std::fs::remove_file(&midi_path);
    result
}

pub fn render_midi_file_to_wav(
    midi_path: &Path,
    soundfont: &Path,
    output: &Path,
    timeout_secs: u64,
) -> Result<(), String> {
    if !soundfont.is_file() {
        return Err(format!(
            "SoundFont no encontrado: {}. Configura SOUNDFONT_PATH para indicar otro.",
            soundfont.display()
        ));
    }

    let result = (|| {
        let mut child = launch_fluidsynth(soundfont, output, midi_path)?;
        let timeout = Duration::from_secs(timeout_secs);

        // Esperar al proceso con timeout
        let start = std::time::Instant::now();
        let status = loop {
            match child.try_wait() {
                Ok(Some(s)) => break s,
                Ok(None) => {
                    if start.elapsed() >= timeout {
                        // Timeout: matar el proceso
                        let _ = kill_tree(child.id());
                        return Err(format!("fluidsynth supero el timeout de {}s", timeout_secs));
                    }
                    std::thread::sleep(Duration::from_millis(100));
                }
                Err(e) => {
                    return Err(format!("error esperando fluidsynth: {e}"));
                }
            }
        };

        if !status.success() {
            return Err(format!("fluidsynth fallo con codigo {:?}", status.code()));
        }
        if !output.exists() {
            return Err("fluidsynth no genero el WAV".into());
        }
        Ok(())
    })();

    if result.is_err() {
        let _ = std::fs::remove_file(output);
    }
    result
}

fn launch_fluidsynth(soundfont: &Path, output: &Path, midi_path: &Path) -> Result<Child, String> {
    Command::new("fluidsynth")
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
        .spawn()
        .map_err(|e| format!("no se pudo ejecutar fluidsynth: {e}"))
}

/// Mata un proceso y sus hijos (solo el proceso directo, sin recursión profunda
/// para evitar complejidad innecesaria en Linux).
fn kill_tree(pid: u32) {
    #[cfg(unix)]
    {
        // En Linux, kill -9 -PID mata todo el grupo de procesos
        let _ = Command::new("kill")
            .arg("-9")
            .arg(format!("-{pid}"))
            .spawn()
            .and_then(|mut c| c.wait());
    }
    #[cfg(not(unix))]
    {
        let _ = Command::new("taskkill")
            .args(&["/F", "/T", "/PID", &pid.to_string()])
            .spawn()
            .and_then(|mut c| c.wait());
    }
}

pub fn default_soundfont() -> PathBuf {
    if let Ok(path) = std::env::var("SOUNDFONT_PATH") {
        return PathBuf::from(path);
    }

    let bundled_soundfont = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("assets")
        .join("TimGM6mb.sf2");
    [
        bundled_soundfont.clone(),
        PathBuf::from("/usr/share/sounds/sf2/TimGM6mb.sf2"),
        PathBuf::from("/usr/share/sounds/sf2/FluidR3_GM.sf2"),
        PathBuf::from("/usr/share/sounds/sf2/default-GM.sf2"),
    ]
    .into_iter()
    .find(|path| path.is_file())
    .unwrap_or(bundled_soundfont)
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use super::{default_soundfont, render_midi_to_wav};

    #[test]
    fn renders_a_midi_file_to_wav_with_the_bundled_soundfont() {
        let midi = [
            b'M', b'T', b'h', b'd', 0, 0, 0, 6, 0, 0, 0, 1, 1, 0xE0, b'M', b'T', b'r', b'k', 0, 0,
            0, 13, 0, 0x90, 60, 100, 0x83, 0x60, 0x80, 60, 0, 0, 0xFF, 0x2F, 0,
        ];
        let directory = std::env::temp_dir().join(format!("alesito-mix-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&directory).unwrap();
        let output = directory.join("render.wav");

        render_midi_to_wav(&midi, &default_soundfont(), &output, 30).unwrap();

        let wav = std::fs::read(&output).unwrap();
        assert!(wav.len() > 44);
        assert_eq!(&wav[..4], b"RIFF");
        assert_eq!(&wav[8..12], b"WAVE");
        std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn bundled_soundfont_is_stored_with_the_rust_backend() {
        let soundfont = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("assets")
            .join("TimGM6mb.sf2");

        assert!(
            soundfont.is_file(),
            "missing bundled SoundFont: {}",
            soundfont.display()
        );
    }
}
