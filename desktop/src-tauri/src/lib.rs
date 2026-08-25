#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::net::TcpListener;
use std::path::PathBuf;

/// %LOCALAPPDATA%/FairyReport（用户私有目录，文件 ACL 继承为仅当前用户）。
fn state_dir() -> Result<PathBuf, String> {
    let local = std::env::var("LOCALAPPDATA").map_err(|_| "LOCALAPPDATA 未设置".to_string())?;
    Ok(PathBuf::from(local).join("FairyReport"))
}

fn state_path() -> Result<PathBuf, String> {
    Ok(state_dir()?.join("desktop-state.json"))
}

/// 选空闲端口：绑定 127.0.0.1:0 取系统分配端口，随即释放。
#[tauri::command]
fn pick_free_port() -> Result<u16, String> {
    let listener = TcpListener::bind("127.0.0.1:0").map_err(|e| e.to_string())?;
    let port = listener.local_addr().map_err(|e| e.to_string())?.port();
    drop(listener);
    Ok(port)
}

/// 引擎子进程工作目录：MVP 开发形态=仓库根（CARGO_MANIFEST_DIR 上两级）。
#[tauri::command]
fn engine_cwd() -> Result<String, String> {
    let manifest = env!("CARGO_MANIFEST_DIR");
    let p = std::path::Path::new(manifest);
    let repo = p.parent().and_then(|x| x.parent()).unwrap_or(p);
    Ok(repo.to_string_lossy().to_string())
}

/// 读取持久化状态文件；不存在返回空串。
#[tauri::command]
fn read_state() -> Result<String, String> {
    let path = state_path()?;
    if !path.exists() {
        return Ok(String::new());
    }
    fs::read_to_string(path).map_err(|e| e.to_string())
}

/// 写入持久化状态文件（目录与文件均位于用户私有 LOCALAPPDATA，ACL 继承为仅当前用户）。
#[tauri::command]
fn write_state(content: String) -> Result<(), String> {
    let dir = state_dir()?;
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let path = state_path()?;
    fs::write(path, content).map_err(|e| e.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            pick_free_port,
            engine_cwd,
            read_state,
            write_state,
        ])
        .run(tauri::generate_context!())
        .expect("error while running FairyReport desktop application");
}
