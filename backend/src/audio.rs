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

    let mut child = launch_fluidsynth(soundfont, output, &midi_path)?;
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
                    return Err(format!(
                        "fluidsynth supero el timeout de {}s",
                        timeout_secs
                    ));
                }
                std::thread::sleep(Duration::from_millis(100));
            }
            Err(e) => {
                return Err(format!("error esperando fluidsynth: {e}"));
            }
        }
    };

    let _ = std::fs::remove_file(&midi_path);
    if !status.success() {
        return Err(format!("fluidsynth fallo con codigo {:?}", status.code()));
    }
    if !output.exists() {
        return Err("fluidsynth no genero el WAV".into());
    }
    Ok(())
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
    std::env::var("SOUNDFONT_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("../frontend/FluidR3_GM.sf2"))
}