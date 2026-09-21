#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;

static LOCAL_ENGINE_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

fn kill_engine_process() {
    if let Ok(mut lock) = LOCAL_ENGINE_PROCESS.lock() {
        if let Some(mut child) = lock.take() {
            let pid = child.id();
            log_debug(&format!("[kill_engine_process] killing engine process tree for PID {}", pid));
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                const CREATE_NO_WINDOW: u32 = 0x08000000;
                // PyInstaller onefile 会先启动引导进程再派生真实 Python 子进程，
                // 必须使用 taskkill /F /T 强杀整棵子进程树，防止遗留后台孤儿进程与文件句柄锁定
                let _ = Command::new("taskkill")
                    .args(&["/F", "/T", "/PID", &pid.to_string()])
                    .creation_flags(CREATE_NO_WINDOW)
                    .status();
            }
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn find_engine_binary() -> Option<PathBuf> {
    let binary_name = if cfg!(windows) {
        "fairyreport-engine.exe"
    } else {
        "fairyreport-engine"
    };

    // 1. 优先在当前正在运行的可执行程序同级目录下寻找（便携绿色解压包）
    if let Ok(current_exe) = std::env::current_exe() {
        if let Some(parent) = current_exe.parent() {
            let candidate = parent.join(binary_name);
            if candidate.exists() {
                return Some(candidate);
            }
        }
    }

    // 2. 检查开发环境/编译目标目录中的 sidecar 二进制
    let manifest = env!("CARGO_MANIFEST_DIR");
    let p = std::path::Path::new(manifest);
    let dev_candidates = [
        p.join("binaries").join(format!(
            "fairyreport-engine-x86_64-pc-windows-msvc{}",
            if cfg!(windows) { ".exe" } else { "" }
        )),
        p.join("binaries").join(binary_name),
        p.join("target").join("release").join(binary_name),
    ];
    for cand in &dev_candidates {
        if cand.exists() {
            return Some(cand.clone());
        }
    }

    None
}

fn log_debug(msg: &str) {
    if let Ok(dir) = state_dir() {
        let _ = fs::create_dir_all(&dir);
        let log_file = dir.join("fairyreport.log");
        if let Ok(mut f) = fs::OpenOptions::new().create(true).append(true).open(log_file) {
            use std::io::Write;
            let _ = writeln!(f, "{}", msg);
        }
    }
}

/// 启动本地独立 Python 引擎（保留系统完整环境变量，Windows 下不弹控制台黑框）
#[tauri::command]
fn start_local_engine(port: u16) -> Result<String, String> {
    log_debug(&format!("[start_local_engine] requested on port {}", port));
    kill_engine_process();

    let engine_bin = match find_engine_binary() {
        Some(bin) => {
            log_debug(&format!("[start_local_engine] found binary at {:?}", bin));
            bin
        }
        None => {
            log_debug("[start_local_engine] error: find_engine_binary returned None");
            return Err("未找到本地独立引擎二进制程序(fairyreport-engine)".to_string());
        }
    };

    let data_dir = state_dir()?;
    let mut cmd = Command::new(&engine_bin);
    cmd.arg("--port").arg(port.to_string());
    cmd.env("ENGINE_DATA_DIR", &data_dir);
    log_debug(&format!("[start_local_engine] using data_dir: {:?}", data_dir));

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    match cmd.spawn() {
        Ok(child) => {
            log_debug(&format!("[start_local_engine] spawned engine PID: {}", child.id()));
            if let Ok(mut lock) = LOCAL_ENGINE_PROCESS.lock() {
                *lock = Some(child);
            }
            Ok(format!("引擎已启动，路径: {:?}", engine_bin))
        }
        Err(e) => {
            log_debug(&format!("[start_local_engine] spawn failed: {}", e));
            Err(format!("启动本地独立引擎失败: {}", e))
        }
    }
}

/// 停止本地独立 Python 引擎
#[tauri::command]
fn stop_local_engine() -> Result<(), String> {
    log_debug("[stop_local_engine] called");
    kill_engine_process();
    Ok(())
}

/// 接收来自前端 JS 的日志输出
#[tauri::command]
fn log_from_js(msg: String) -> Result<(), String> {
    log_debug(&format!("[JS] {}", msg));
    Ok(())
}

/// 检查指定端口上的引擎是否健康就绪（直接发起 TCP 请求，不受 WebView/CORS/URL Scope 限制）
#[tauri::command]
fn check_engine_health(port: u16) -> Result<bool, String> {
    use std::io::{Read, Write};
    use std::net::{SocketAddr, TcpStream};
    use std::time::Duration;

    let addr: SocketAddr = match format!("127.0.0.1:{}", port).parse() {
        Ok(a) => a,
        Err(e) => return Err(format!("地址解析失败: {}", e)),
    };

    let mut stream = match TcpStream::connect_timeout(&addr, Duration::from_millis(500)) {
        Ok(s) => s,
        Err(_) => return Ok(false),
    };

    let _ = stream.set_read_timeout(Some(Duration::from_millis(1000)));
    let req = format!("GET /health HTTP/1.1\r\nHost: 127.0.0.1:{}\r\nConnection: close\r\n\r\n", port);
    if stream.write_all(req.as_bytes()).is_err() {
        return Ok(false);
    }

    let mut buf = [0u8; 512];
    match stream.read(&mut buf) {
        Ok(n) if n > 0 => {
            let resp = String::from_utf8_lossy(&buf[..n]);
            let ok = resp.contains("200 OK") || resp.contains("\"status\":\"ok\"");
            if ok {
                log_debug(&format!("[check_engine_health] port {} is ready (200 OK)", port));
            }
            Ok(ok)
        }
        _ => Ok(false),
    }
}

/// 数据目录：优先检测是否为便携绿色模式（exe 同级存在 .portable 标记或 data 目录），否则回退到 %LOCALAPPDATA%/FairyReport。
fn state_dir() -> Result<PathBuf, String> {
    if let Ok(current_exe) = std::env::current_exe() {
        if let Some(parent) = current_exe.parent() {
            let portable_flag = parent.join(".portable");
            let portable_data = parent.join("data");
            if portable_flag.exists() || portable_data.exists() {
                let _ = fs::create_dir_all(&portable_data);
                return Ok(portable_data);
            }
        }
    }
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
    log_debug(&format!("[pick_free_port] allocated port {}", port));
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

/// 读取持久化状态文件；不存在返回空串，自动剥除 UTF-8 BOM 防止 JSON.parse 异常。
#[tauri::command]
fn read_state() -> Result<String, String> {
    let path = state_path()?;
    if !path.exists() {
        log_debug("[read_state] state file does not exist");
        return Ok(String::new());
    }
    log_debug(&format!("[read_state] read state from {:?}", path));
    let content = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let sanitized = content.trim_start_matches('\u{feff}').to_string();
    Ok(sanitized)
}

/// 写入持久化状态文件（目录与文件均位于用户私有 LOCALAPPDATA，ACL 继承为仅当前用户）。
#[tauri::command]
fn write_state(content: String) -> Result<(), String> {
    let dir = state_dir()?;
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let path = state_path()?;
    fs::write(path, content).map_err(|e| e.to_string())
}

/// 读取本地文件二进制字节数组（用于跨网向云端引擎上传资料）
#[tauri::command]
fn read_file_binary(path: String) -> Result<Vec<u8>, String> {
    fs::read(&path).map_err(|e| e.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_dialog::init())
        .on_window_event(|_window, event| {
            match event {
                tauri::WindowEvent::CloseRequested { .. } | tauri::WindowEvent::Destroyed => {
                    kill_engine_process();
                }
                _ => {}
            }
        })
        .invoke_handler(tauri::generate_handler![
            pick_free_port,
            engine_cwd,
            read_state,
            write_state,
            read_file_binary,
            start_local_engine,
            stop_local_engine,
            check_engine_health,
            log_from_js,
        ])
        .build(tauri::generate_context!())
        .expect("error while running FairyReport desktop application");

    app.run(|_app_handle, event| {
        match event {
            tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
                kill_engine_process();
            }
            _ => {}
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_find_engine() {
        let bin = find_engine_binary();
        println!("Found engine binary: {:?}", bin);
        assert!(bin.is_some(), "Engine binary should be found");
    }

    #[test]
    fn test_start_and_stop_engine() {
        let res = start_local_engine(8035);
        println!("start_local_engine result: {:?}", res);
        assert!(res.is_ok());

        // Wait a brief moment and verify child is stored
        let has_child = {
            let lock = LOCAL_ENGINE_PROCESS.lock().unwrap();
            lock.is_some()
        };
        assert!(has_child, "Engine child process should be stored in mutex");

        let stop_res = stop_local_engine();
        assert!(stop_res.is_ok());
    }

    #[test]
    fn test_state_dir() {
        let dir = state_dir().expect("state_dir should succeed");
        println!("State dir: {:?}", dir);
        assert!(!dir.as_os_str().is_empty());
    }

    #[test]
    fn test_portable_detection() {
        let exe = std::env::current_exe().unwrap();
        let parent = exe.parent().unwrap();
        let portable_flag = parent.join(".portable");
        let portable_data = parent.join("data");
        let _ = fs::write(&portable_flag, "");
        let dir = state_dir().expect("state_dir should succeed in portable mode");
        assert_eq!(dir, portable_data);
        let _ = fs::remove_file(&portable_flag);
        let _ = fs::remove_dir_all(&portable_data);
    }
}
