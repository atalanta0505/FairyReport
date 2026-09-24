"""
FairyReport 独立引擎打包脚本 (PyInstaller)

将 engine/app/main.py 冻结为独立可执行二进制，供 Tauri Sidecar 或独立运行。
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

    # 添加本地快速向量模型 (若存在)
    model_dir = REPO_ROOT / "data" / "fastembed_models"
    if model_dir.exists():
        cmd.extend(["--add-data", f"{model_dir}{sep}data/fastembed_models"])
    # 入口脚本
    entry_point = REPO_ROOT / "engine" / "entrypoint.py"
    cmd.append(str(entry_point))

    print(f"[*] 开始构建独立引擎二进制：{binary_name}{ext}")
    print(f"[*] 执行命令：{' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        print(f"[!] PyInstaller 构建失败，退出码：{result.returncode}")
        sys.exit(result.returncode)

    target_file = output_dir / f"{binary_name}{ext}"
    if target_file.exists():
        print(f"[+] 成功构建独立引擎：{target_file} ({target_file.stat().st_size / (1024*1024):.1f} MB)")
        import shutil
        for sub in ["debug", "release"]:
            dest_dir = REPO_ROOT / "desktop" / "src-tauri" / "target" / sub
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
