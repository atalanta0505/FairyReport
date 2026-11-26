"""
FairyReport 独立引擎打包脚本 (PyInstaller)

将 engine/entrypoint.py 冻结为独立可执行二进制，同时支持：
  - 桌面端 Tauri Sidecar FastAPI 引擎（默认运行）
  - 零 Python 环境 MCP Server（传入 --mcp 参数）
产物路径：desktop/src-tauri/binaries/fairyreport-engine-<target-triple>.exe
"""
import os
import platform
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_target_triple() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        return "x86_64-pc-windows-msvc"
    elif system == "darwin":
        if "arm" in machine or "aarch64" in machine:
            return "aarch64-apple-darwin"
        return "x86_64-apple-darwin"
    elif system == "linux":
        if "aarch64" in machine:
            return "aarch64-unknown-linux-gnu"
        return "x86_64-unknown-linux-gnu"
    else:
        return f"{machine}-unknown-{system}"


def build():
    system = platform.system().lower()
    triple = get_target_triple()
    ext = ".exe" if system == "windows" else ""
    binary_name = f"fairyreport-engine-{triple}"
    output_dir = REPO_ROOT / "desktop" / "src-tauri" / "binaries"
    output_dir.mkdir(parents=True, exist_ok=True)

    sep = ";" if system == "windows" else ":"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        binary_name,
        "--distpath",
        str(output_dir),
        "--workpath",
        str(REPO_ROOT / "build_engine_pyinstaller"),
        "--specpath",
        str(REPO_ROOT / "build_engine_pyinstaller"),
        "--onefile",
        # 收集核心数据包
        "--collect-all",
        "chromadb",
        "--collect-all",
        "fastembed",
        "--collect-all",
        "onnxruntime",
        "--collect-all",
        "mcp",
        # 隐藏导入
        "--hidden-import",
        "uvicorn.logging",
        "--hidden-import",
        "uvicorn.loops.auto",
        "--hidden-import",
        "uvicorn.protocols.http.auto",
        "--hidden-import",
        "uvicorn.lifespan.on",
        "--hidden-import",
        "engine.app.main",
        "--hidden-import",
        "engine.mcp_server",
        "--hidden-import",
        "sse_starlette",
        "--hidden-import",
        "jsonschema",
        "--hidden-import",
        "engine.app.projects.router",
        "--hidden-import",
        "engine.app.materials.router",
        "--hidden-import",
        "engine.app.generic.router",
        "--hidden-import",
        "engine.app.writing.router",
        "--hidden-import",
        "engine.app.export.router",
        "--hidden-import",
        "engine.app.writing.context_verifier",
        "--hidden-import",
        "sqlite3",
        "--hidden-import",
        "docx2txt",
        "--hidden-import",
        "docx",
        "--hidden-import",
        "openpyxl",
        "--hidden-import",
        "markdownify",
        "--hidden-import",
        "jinja2",
        "--hidden-import",
        "beautifulsoup4",
        "--hidden-import",
        "pypdf",
        # 排除庞大的不相关依赖（如 torch / pandas / scipy / streamlit 等）
        "--exclude-module",
        "torch",
        "--exclude-module",
        "torchvision",
        "--exclude-module",
        "torchaudio",
        "--exclude-module",
        "transformers",
        "--exclude-module",
        "sentence_transformers",
        "--exclude-module",
        "scipy",
        "--exclude-module",
        "pandas",
        "--exclude-module",
        "matplotlib",
        "--exclude-module",
        "pytest",
        "--exclude-module",
        "streamlit",
        "--exclude-module",
        "altair",
        "--exclude-module",
        "pydeck",
        "--exclude-module",
        "playwright",
        "--exclude-module",
        "tkinter",
    ]

    # 离线向量模型由 pack_portable.py 直接置于外层 data/fastembed_models/，
    # 不再压入 --onefile 内部，避免每次启动解压上百 MB 模型至 %TEMP% 拖慢启动速度。
    # 添加 Word 报告专属模板包 (若存在)
    pattern_dir = REPO_ROOT / "pattern"
    if pattern_dir.exists():
        cmd.extend(["--add-data", f"{pattern_dir}{sep}pattern"])
    # 添加内置 15 类报告 JSON 模板库 (若存在)
    templates_dir = REPO_ROOT / "generic_knowledge" / "templates"
    if templates_dir.exists():
        cmd.extend(["--add-data", f"{templates_dir}{sep}generic_knowledge/templates"])
    # 入口脚本
    entry_point = REPO_ROOT / "engine" / "entrypoint.py"
    cmd.append(str(entry_point))

    print(f"[*] 开始构建独立引擎二进制：{binary_name}{ext}")
    print(f"[*] 执行命令：{' '.join(cmd)}")

    # 净化 Windows 构建期 PATH：确保 C:\Windows\System32 排在最前，并剔除声卡驱动 / TexLive / WPT 等目录，
    # 防止 PyInstaller 误收集第三方目录中过旧的 msvcp140.dll 或 api-ms-win-* 垫片导致 onnxruntime 初始化崩溃(WinError 1114)。
    build_env = os.environ.copy()
    if system == "windows":
        sys_root = build_env.get("SystemRoot", r"C:\Windows")
        sys32 = os.path.join(sys_root, "System32")
        poison_keywords = ("hwaudiodriver", "windows performance toolkit", "texlive")
        filtered_paths = [
            p for p in build_env.get("PATH", "").split(os.pathsep)
            if p and not any(k in p.lower() for k in poison_keywords)
        ]
        build_env["PATH"] = os.pathsep.join([sys32, *filtered_paths])

    result = subprocess.run(cmd, cwd=str(REPO_ROOT), env=build_env)
    if result.returncode != 0:
        print(f"[!] PyInstaller 构建失败，退出码：{result.returncode}")
        sys.exit(result.returncode)

    target_file = output_dir / f"{binary_name}{ext}"
    if target_file.exists():
        print(f"[+] 成功构建独立引擎：{target_file} ({target_file.stat().st_size / (1024*1024):.1f} MB)")
        import shutil
        sync_dirs = [
            REPO_ROOT / "desktop" / "src-tauri" / "target" / "debug",
            REPO_ROOT / "desktop" / "src-tauri" / "target" / "release",
            REPO_ROOT / "desktop" / "src-tauri" / "target" / "x86_64-pc-windows-gnu" / "release",
            REPO_ROOT / "desktop" / "src-tauri" / "target" / "x86_64-pc-windows-msvc" / "release",
        ]
        for dest_dir in sync_dirs:
            if dest_dir.exists():
                dest_file = dest_dir / f"fairyreport-engine{ext}"
                try:
                    shutil.copy2(target_file, dest_file)
                    print(f"[+] 同步更新运行目录引擎: {dest_file}")
                except Exception as e:
                    print(f"[!] 无法更新 {dest_file} (可能因客户端正在运行被锁定，请关闭客户端后重启): {e}")
    else:
        print(f"[!] 未找到预期的构建产物：{target_file}")
        sys.exit(1)


if __name__ == "__main__":
    build()
