use std::net::SocketAddr;
use std::path::PathBuf;

use tauri::Manager;

fn backend_addr() -> SocketAddr {
    "127.0.0.1:3000".parse().expect("direccion valida")
}

fn configure_runtime_paths(app: &tauri::App) {
    let Ok(resource_dir) = app.path().resource_dir() else { return; };
    set_if_exists("SOUNDFONT_PATH", resource_dir.join("assets").join("TimGM6mb.sf2"));
    set_if_exists("WEB_DIST_DIR", resource_dir.join("web-dist"));
    set_if_exists("FLUIDSYNTH_BIN", bundled_fluidsynth(&resource_dir));
    set_default_model_dir(app);
}

fn bundled_fluidsynth(resource_dir: &PathBuf) -> PathBuf {
    if cfg!(target_os = "windows") {
        return resource_dir.join("bin").join("fluidsynth.exe");
    }
    resource_dir.join("bin").join("fluidsynth")
}

fn set_if_exists(key: &str, path: PathBuf) {
    if path.exists() {
        std::env::set_var(key, path);
    }
}

fn set_default_model_dir(app: &tauri::App) {
    if std::env::var_os("MODEL_DIR").is_some() {
        return;
    }
    let Ok(app_data) = app.path().app_data_dir() else { return; };
    let model_dir = app_data.join("models").join("basic-pitch").join("icassp-2022");
    std::env::set_var("MODEL_DIR", model_dir);
}

fn spawn_backend() {
    tauri::async_runtime::spawn(async move {
        if let Err(error) = run_backend().await {
            eprintln!("Error iniciando backend: {error}");
            eprintln!("Verifica MODEL_DIR, SOUNDFONT_PATH, FLUIDSYNTH_BIN y dependencias del sistema.");
        }
    });
}

async fn run_backend() -> Result<(), String> {
    let state = alesito_backend::create_state().await;
    alesito_backend::spawn_cleanup_task(state.clone());
    let web_dist = alesito_backend::resolve_web_dist_dir();
    let app = alesito_backend::build_router(state, web_dist);
    alesito_backend::serve(app, backend_addr())
        .await
        .map_err(|e| e.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            configure_runtime_paths(app);
            spawn_backend();
            #[cfg(not(debug_assertions))]
            if let Some(window) = app.get_webview_window("main") {
                let url = "http://127.0.0.1:3000".parse().expect("url valida");
                let _ = window.navigate(url);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error al ejecutar la aplicación Tauri");
}
