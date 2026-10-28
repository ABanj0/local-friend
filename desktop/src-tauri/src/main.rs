#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{io::{BufRead, BufReader, Read, Write}, path::PathBuf, process::{Child, Command, Stdio}, sync::Mutex};
use serde::Serialize;
use tauri::Manager;
mod diagnostics;
mod first_run;

#[derive(Clone, Serialize)]
struct Connection { port: u16, token: String }
struct Backend { child: Child, connection: Connection }
struct State { backend: Mutex<Option<Backend>>, diagnostics: diagnostics::Shared }

impl Drop for Backend {
    fn drop(&mut self) { stop(self); }
}

fn stop(backend: &mut Backend) {
    if let Some(mut input) = backend.child.stdin.take() { let _ = input.write_all(b"shutdown\n"); }
    for _ in 0..50 {
        if matches!(backend.child.try_wait(), Ok(Some(_))) { return; }
        std::thread::sleep(std::time::Duration::from_millis(100));
    }
    let _ = backend.child.kill();
    let _ = backend.child.wait();
}

fn spawn(app: &tauri::AppHandle, diagnostics: diagnostics::Shared) -> Result<Backend, String> {
    let (command, config): (Command, PathBuf) = if cfg!(debug_assertions) {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().map_err(|e| e.to_string())?;
        let python = root.join(".venv/Scripts/python.exe");
        if !python.exists() { return Err("Python environment missing. Run scripts/setup-desktop.ps1.".into()); }
        let mut cmd = Command::new(python);
        cmd.args(["-m", "local_agent.studio.runtime"]).current_dir(&root);
        (cmd, root.join("agent.toml"))
    } else {
        let data = app.path().app_local_data_dir().map_err(|e| e.to_string())?;
        std::fs::create_dir_all(&data).map_err(|e| e.to_string())?;
        let config = data.join("agent.toml");
        let resource = app.path().resource_dir().map_err(|e| e.to_string())?.join("resources/agent.toml");
        first_run::initialize(&config, &resource).map_err(|e| format!("Cannot initialize configuration: {e}"))?;
        let exe = std::env::current_exe().map_err(|e| e.to_string())?.with_file_name("agent-backend.exe");
        (Command::new(exe), config)
    };
    launch(command, config, diagnostics)
}

fn launch(mut command: Command, config: PathBuf, diagnostics: diagnostics::Shared) -> Result<Backend, String> {
    let token = format!("{}{}", uuid::Uuid::new_v4().simple(), uuid::Uuid::new_v4().simple());
    command.arg("--config").arg(config).env("LOCAL_AGENT_STUDIO_TOKEN", &token)
        .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
    #[cfg(windows)] {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let child = command.spawn().map_err(|e| format!("Backend launch failed: {e}"))?;
    // From here every error drops the owner, stopping and reaping this child.
    let mut backend = Backend { child, connection: Connection { port: 0, token: token.clone() } };
    let stderr = backend.child.stderr.take().ok_or("Backend stderr unavailable")?;
    let stderr_output = diagnostics.clone();
    let stderr_token = token.clone();
    std::thread::spawn(move || diagnostics::drain(stderr, stderr_output, stderr_token));
    let stdout = backend.child.stdout.take().ok_or("Backend stdout unavailable")?;
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let mut reader = BufReader::new(stdout);
        let mut line = String::new();
        let result = reader.by_ref().take(16_385).read_line(&mut line).map(|_| line);
        let _ = tx.send(result);
        diagnostics::drain(reader, diagnostics, token);
    });
    let startup = rx.recv_timeout(std::time::Duration::from_secs(20));
    let line = match startup {
        Ok(Ok(line)) => line,
        _ => { return Err("Backend did not start within 20 seconds. Inspect backend diagnostics.".into()); }
    };
    if line.len() > 16_384 { return Err("Backend readiness exceeded its size limit.".into()); }
    let info: serde_json::Value = match serde_json::from_str(&line) {
        Ok(value) => value,
        Err(_) => { return Err("Backend exited before readiness. Check Python dependencies and backend diagnostics.".into()); }
    };
    if let Some(error) = info.get("error").and_then(|v| v.as_str()) {
        return Err(diagnostics::safe(error, &backend.connection.token));
    }
    backend.connection.port = info.get("port").and_then(|v| v.as_u64())
        .and_then(|v| u16::try_from(v).ok()).filter(|v| *v != 0)
        .ok_or("Backend returned invalid readiness port")?;
    Ok(backend)
}

#[tauri::command]
fn backend_connection(app: tauri::AppHandle, state: tauri::State<State>) -> Result<Connection, String> {
    let mut slot = state.backend.lock().map_err(|e| e.to_string())?;
    if let Some(backend) = slot.as_mut() {
        if backend.child.try_wait().map_err(|e| e.to_string())?.is_none() { return Ok(backend.connection.clone()); }
    }
    let backend = spawn(&app, state.diagnostics.clone())?;
    let connection = backend.connection.clone();
    *slot = Some(backend);
    Ok(connection)
}

#[tauri::command]
fn restart_backend(app: tauri::AppHandle, state: tauri::State<State>) -> Result<Connection, String> {
    { let mut slot = state.backend.lock().map_err(|e| e.to_string())?;
      if let Some(mut backend) = slot.take() { stop(&mut backend); } }
    backend_connection(app, state)
}

#[tauri::command]
fn backend_diagnostics(state: tauri::State<State>) -> Result<String, String> {
    Ok(state.diagnostics.lock().map_err(|e| e.to_string())?.text())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") { let _ = window.set_focus(); }
        }))
        .plugin(tauri_plugin_dialog::init())
        .manage(State { backend: Mutex::new(None), diagnostics: diagnostics::Shared::default() })
        .invoke_handler(tauri::generate_handler![backend_connection, restart_backend, backend_diagnostics])
        .build(tauri::generate_context!()).expect("Failed to build desktop application")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                let shared = app.state::<State>();
                if let Ok(mut state) = shared.backend.lock() {
                    if let Some(mut backend) = state.take() { stop(&mut backend); }
                };
            }
        });
}

#[cfg(test)]
mod lifecycle_tests {
    use super::*;

    fn python() -> Command {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
        let mut command = Command::new(root.join(".venv/Scripts/python.exe"));
        command.current_dir(root);
        command
    }

    #[test]
    fn malformed_readiness_stops_and_reaps_owned_child() {
        let path = std::env::temp_dir().join(format!("studio-lifecycle-{}.txt", uuid::Uuid::new_v4()));
        let mut command = python();
        command.args(["-u", "-c", "import sys; print('invalid-readiness',flush=True); sys.stdin.readline(); open(sys.argv[-1],'w').write('shutdown received')"]);
        let result = launch(command, path.clone(), diagnostics::Shared::default());
        assert!(result.is_err());
        assert_eq!(std::fs::read_to_string(&path).unwrap(), "shutdown received");
        std::fs::remove_file(path).unwrap();
    }

    #[test]
    fn native_launcher_reports_real_missing_configuration() {
        let mut command = python();
        command.args(["-m", "local_agent.studio.runtime", "--port", "0"]);
        let path = std::env::temp_dir().join(format!("missing-{}.toml", uuid::Uuid::new_v4()));
        match launch(command, path, diagnostics::Shared::default()) {
            Err(error) => assert!(error.contains("Cannot load configuration"), "{error}"),
            Ok(_) => panic!("Missing configuration was accepted"),
        }
    }
}
