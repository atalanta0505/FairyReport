"""
FairyReport 纯净开发源码包打包脚本
生成目标：dist/FairyReport-Dev-Source-v1.6.1.zip
用途：将本项目打包迁移至另一台未配置环境的 Windows 电脑接续开发
特性：
1. 包含完整前后端源码、Tauri 桌面外壳、测试套件、构建脚本、行业规程与15类Word模板；
2. 包含离线中文向量嵌入模型 (data/fastembed_models ~240MB)，免去新电脑连外网下模型的困难；
3. 严格剔除 .env 密钥、个人项目业务数据 (data/projects/)、node_modules 与数GB的 Rust 编译缓存；
4. 附带《新电脑开发环境搭建与快速启动指引.md》，新电脑解压即照着指引搭建环境。
"""
import os
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

# 确保在 Windows 控制台下支持 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
PACKAGE_NAME = "FairyReport-Dev-Source-v1.6.1"
STAGE_DIR = DIST_DIR / "stage_dev_pack" / PACKAGE_NAME
OUTPUT_ZIP = DIST_DIR / f"{PACKAGE_NAME}.zip"

# 绝对排除的目录
EXCLUDE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".github",
    ".vscode",
    ".idea",
    "node_modules",
    "target",
    "binaries",
    "projects",
    "site",
    "dist",
    "stage_cloud_deploy",
    "stage_dev_pack",
    "build",
    "build_engine_pyinstaller",
}

# 绝对排除的扩展名
EXCLUDE_EXTS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".sqlite",
    ".db",
}

def safe_copy_tree(src: Path, dst: Path, ignore_names=None):
    """递归拷贝目录，自动过滤缓存与敏感目录。"""
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        if entry.name in EXCLUDE_DIRS:
            continue
        if entry.name.startswith(".env") and entry.name != ".env.example":
            continue
        if ignore_names and entry.name in ignore_names:
            continue

        target = dst / entry.name
        if entry.is_dir():
            safe_copy_tree(entry, target, ignore_names)
        else:
            if entry.suffix.lower() in EXCLUDE_EXTS:
                continue
            shutil.copy2(entry, target)

def audit_staged_files(stage_root: Path):
    """深度安全与纯净度审计。"""
    print("\n[AUDIT] 正在对开发包预选文件执行深度安全与纯净度审计...")
    violations = []
    total_files = 0
    total_bytes = 0

    key_regex = re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE)

    for root, dirs, files in os.walk(stage_root):
        rel_root = Path(root).relative_to(stage_root)

        for d in list(dirs):
            if d in EXCLUDE_DIRS:
                violations.append(f"发现违规目录: {rel_root / d}")
            if "project" in d.lower() and "data" in str(rel_root).lower():
                violations.append(f"发现个人业务项目目录: {rel_root / d}")

        for f in files:
            file_path = Path(root) / f
            rel_file = rel_root / f
            total_files += 1
            total_bytes += file_path.stat().st_size

            # 1. 检查凭据文件名
            if (f.startswith(".env") and f != ".env.example") or f.endswith(".key") or f.endswith(".pem"):
                violations.append(f"发现敏感凭据文件: {rel_file}")

            # 2. 检查缓存与临时文件
            if file_path.suffix.lower() in EXCLUDE_EXTS:
                violations.append(f"发现临时缓存文件: {rel_file}")

            # 3. 扫描文本文件内容中的潜在硬编码密钥（排除 .env.example 及超大文件）
            if f != ".env.example" and file_path.stat().st_size < 1024 * 1024 and file_path.suffix.lower() in {
                ".py", ".json", ".ts", ".vue", ".html", ".js", ".md", ".sh", ".bat", ".yml", ".yaml", ".txt"
            }:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    matches = key_regex.findall(content)
                    for m in matches:
                        lower_m = m.lower()
                        if "xxxx" in lower_m or "your" in lower_m or "placeholder" in lower_m or "example" in lower_m:
                            continue
                        violations.append(f"文件内容包含疑似硬编码真实 API Key: {rel_file} ({m[:6]}...)")
                except Exception:
                    pass

    if violations:
        print("[FAIL] 审计未通过，存在以下违规项：")
        for v in violations:
            print(f"  - {v}")
        raise RuntimeError("安全审计失败，打包终止！")

    print(f"[OK] 审计 100% 通过！共扫描 {total_files} 个文件（未压缩总计 {total_bytes / (1024*1024):.1f} MB）。")
    print("  * 0 敏感凭据 (.env / 个人 API Key)")
    print("  * 0 个人业务项目数据 (data/projects/)")
    print("  * 0 开发与构建杂质 (node_modules / target / __pycache__)")

def main():
    start_time = time.time()
    print("==================================================")
    print("  FairyReport 纯净接续开发源码包构建")
    print(f"  目标版本: {PACKAGE_NAME}")
    print("==================================================")

    # 1. 清理临时暂存区
    if STAGE_DIR.parent.exists():
        shutil.rmtree(STAGE_DIR.parent, ignore_errors=True)
    STAGE_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[PACK] 正在收集与装配接续开发源码资产...")

    # (1) 完整 Python 后端引擎（含测试）
    print("  -> 拷贝 engine/ ...")
    safe_copy_tree(REPO_ROOT / "engine", STAGE_DIR / "engine")

    # (2) 完整前端工程与桌面外壳（排除 node_modules 与 target）
    print("  -> 拷贝 desktop/ (前端Vue3源码 + Tauri2外壳) ...")
    safe_copy_tree(REPO_ROOT / "desktop", STAGE_DIR / "desktop")

    # (3) 通用行业规程库
    print("  -> 拷贝 generic_knowledge/ ...")
    safe_copy_tree(REPO_ROOT / "generic_knowledge", STAGE_DIR / "generic_knowledge")

    # (4) 15 类国家级出版模板
    print("  -> 拷贝 pattern/ (15 类标准 Word 模板) ...")
    safe_copy_tree(REPO_ROOT / "pattern", STAGE_DIR / "pattern")

    # (5) 开发与构建脚本
    print("  -> 拷贝 scripts/ ...")
    safe_copy_tree(REPO_ROOT / "scripts", STAGE_DIR / "scripts")

    # (6) 文档与架构规范
    if (REPO_ROOT / "docs").is_dir():
        print("  -> 拷贝 docs/ ...")
        safe_copy_tree(REPO_ROOT / "docs", STAGE_DIR / "docs")

    # (7) 离线向量模型 (免去新电脑科学上网下载困扰)
    model_src = REPO_ROOT / "data" / "fastembed_models"
    if model_src.is_dir():
        print("  -> 拷贝 data/fastembed_models/ (离线中文嵌入模型) ...")
        safe_copy_tree(model_src, STAGE_DIR / "data" / "fastembed_models")

    # (8) 纯净数据目录结构
    (STAGE_DIR / "data").mkdir(parents=True, exist_ok=True)

    # (9) 根目录核心配置文件
    root_files = [
        "requirements.txt",
        "pytest.ini",
        "AGENTS.md",
        "README.md",
        ".env.example",
        ".gitignore",
        "Dockerfile",
        "docker-compose.yml",
        ".dockerignore",
        "start_cloud.sh",
        "start_cloud.bat",
        "新电脑开发环境搭建与快速启动指引.md",
        "云端部署操作手册.md",
        "云端部署与浏览器访问指引.md",
    ]
    for rf in root_files:
        p = REPO_ROOT / rf
        if p.is_file():
            print(f"  -> 拷贝 {rf} ...")
            shutil.copy2(p, STAGE_DIR / rf)

    # 2. 执行深度安全与纯净度审计
    audit_staged_files(STAGE_DIR)

    # 3. 生成 ZIP 压缩包
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()

    print(f"\n[ZIP] 正在压缩生成 {OUTPUT_ZIP.name} ...")
    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        for root, dirs, files in os.walk(STAGE_DIR):
            for d in dirs:
                dir_full = Path(root) / d
                dir_rel = dir_full.relative_to(STAGE_DIR.parent).as_posix() + "/"
                zf.writestr(dir_rel, "")
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(STAGE_DIR.parent).as_posix()
                zf.write(full_path, rel_path)

    # 4. 清理暂存区
    shutil.rmtree(STAGE_DIR.parent, ignore_errors=True)

    elapsed = time.time() - start_time
    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print("\n==================================================")
    print(f"[SUCCESS] 纯净接续开发源码包打包成功！")
    print(f"产物路径: {OUTPUT_ZIP}")
    print(f"压缩包体积: {zip_size_mb:.1f} MB")
    print(f"耗时: {elapsed:.1f} 秒")
    print("==================================================")

if __name__ == "__main__":
    main()
