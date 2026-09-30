"""
FairyReport 云端 Web 部署纯净源码包打包脚本
生成目标：dist/FairyReport-Cloud-Deploy-v1.6.2.zip
特性：
1. 包含完整 Python 后端、离线向量模型、15类出版级 Word 模板包；
2. 包含已编译好的前端静态网页 desktop/dist/ 及前端源码；
3. 包含 Dockerfile、docker-compose.yml、启动脚本与详细部署指引；
4. 严格执行 0 敏感凭据、0 业务数据、0 开发编译杂质审计。
"""
import os
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

# 确保在 Windows GBK 控制台下也能正常输出 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
PACKAGE_NAME = "FairyReport-Cloud-Deploy-v1.6.2"
STAGE_DIR = DIST_DIR / "stage_cloud_deploy" / PACKAGE_NAME
OUTPUT_ZIP = DIST_DIR / f"{PACKAGE_NAME}.zip"

# 忽略的文件/目录模式
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
    "stage_cloud_deploy",
    "build",
}

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
        if entry.name.startswith(".env"):
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
    print("\n[AUDIT] 正在对预打包文件执行深度安全与纯净度审计...")
    violations = []
    total_files = 0
    total_bytes = 0

    key_regex = re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE)

    for root, dirs, files in os.walk(stage_root):
        rel_root = Path(root).relative_to(stage_root)

        for d in list(dirs):
            rel_dir_posix = (rel_root / d).as_posix()
            if d in EXCLUDE_DIRS:
                violations.append(f"发现违规目录: {rel_root / d}")
            if "project" in d.lower() and "data" in str(rel_root).lower():
                violations.append(f"发现个人业务项目目录: {rel_root / d}")
            if d == "dist" and rel_dir_posix != "desktop/dist":
                violations.append(f"发现违规构建目录: {rel_root / d}")

        for f in files:
            file_path = Path(root) / f
            rel_file = rel_root / f
            total_files += 1
            total_bytes += file_path.stat().st_size

            # 1. 检查凭据文件名
            if f.startswith(".env") or f.endswith(".key") or f.endswith(".pem"):
                violations.append(f"发现敏感凭据文件: {rel_file}")

            # 2. 检查缓存与临时文件
            if file_path.suffix.lower() in EXCLUDE_EXTS:
                violations.append(f"发现临时缓存文件: {rel_file}")

            # 3. 扫描文本文件内容中的潜在硬编码密钥（排除超大二进制模型文件）
            if file_path.stat().st_size < 1024 * 1024 and file_path.suffix.lower() in {
                ".py", ".json", ".ts", ".vue", ".html", ".js", ".md", ".sh", ".bat", ".yml", ".yaml", ".txt"
            }:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if key_regex.search(content):
                        violations.append(f"文件内容包含疑似硬编码 API Key: {rel_file}")
                except Exception:
                    pass

    if violations:
        print("[FAIL] 审计未通过，存在以下安全隐患：")
        for v in violations:
            print(f"  - {v}")
        raise RuntimeError("安全审计失败，打包终止！")

    print(f"[OK] 审计 100% 通过！共扫描 {total_files} 个文件（未压缩总计 {total_bytes / (1024*1024):.1f} MB）。")
    print("  * 0 敏感凭据 (.env / API Key)")
    print("  * 0 业务项目数据 (data/projects/)")
    print("  * 0 开发与构建杂质 (.git / node_modules / target / __pycache__)")

def main():
    start_time = time.time()
    print("==================================================")
    print("  FairyReport 云端部署纯净源码包自动化构建")
    print(f"  目标版本: {PACKAGE_NAME}")
    print("==================================================")

    # 1. 确认前端生产静态包最新
    dist_index = REPO_ROOT / "desktop" / "dist" / "index.html"
    if not dist_index.is_file():
        print("[WARN] 未检测到 desktop/dist/index.html，开始执行前端构建...")
        ret = os.system(f"pnpm --dir \"{REPO_ROOT / 'desktop'}\" build")
        if ret != 0:
            print("[FAIL] 前端构建失败！")
            sys.exit(1)
    else:
        print("[OK] 前端构建产物就绪 (desktop/dist/)")

    # 2. 清理临时暂存区
    if STAGE_DIR.parent.exists():
        shutil.rmtree(STAGE_DIR.parent, ignore_errors=True)
    STAGE_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[PACK] 正在收集与装配部署资产...")

    # (1) 核心计算引擎
    print("  -> 拷贝 engine/ ...")
    safe_copy_tree(REPO_ROOT / "engine", STAGE_DIR / "engine")

    # (2) 规程规则库
    print("  -> 拷贝 generic_knowledge/ ...")
    safe_copy_tree(REPO_ROOT / "generic_knowledge", STAGE_DIR / "generic_knowledge")

    # (3) 15 类国家级出版模板
    print("  -> 拷贝 pattern/ (15 类标准 Word 模板) ...")
    safe_copy_tree(REPO_ROOT / "pattern", STAGE_DIR / "pattern")

    # (4) 前端编译产物 (供后端单端口托管)
    print("  -> 拷贝 desktop/dist/ (编译就绪的前端静态网页) ...")
    safe_copy_tree(REPO_ROOT / "desktop" / "dist", STAGE_DIR / "desktop" / "dist")

    # (5) 前端源码 (供开发者二次定制)
    print("  -> 拷贝 desktop/ (前端源码及配置文件) ...")
    desktop_stage = STAGE_DIR / "desktop"
    safe_copy_tree(REPO_ROOT / "desktop" / "src", desktop_stage / "src")
    for f in ["package.json", "tsconfig.json", "tsconfig.node.json", "vite.config.ts", "index.html"]:
        p = REPO_ROOT / "desktop" / f
        if p.is_file():
            shutil.copy2(p, desktop_stage / f)

    # (6) 离线向量模型 (方案 A: 自包含 ~240MB)
    model_src = REPO_ROOT / "data" / "fastembed_models"
    if model_src.is_dir():
        print("  -> 拷贝 data/fastembed_models/ (离线中文嵌入模型) ...")
        safe_copy_tree(model_src, STAGE_DIR / "data" / "fastembed_models")

    # (7) 纯净数据目录结构
    (STAGE_DIR / "data").mkdir(parents=True, exist_ok=True)

    # (8) 部署配置文件与脚本
    deploy_files = [
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        ".dockerignore",
        "start_cloud.sh",
        "start_cloud.bat",
        "云端部署操作手册.md",
        "云端部署与浏览器访问指引.md",
    ]
    for df in deploy_files:
        p = REPO_ROOT / df
        if p.is_file():
            print(f"  -> 拷贝 {df} ...")
            shutil.copy2(p, STAGE_DIR / df)

    # 3. 执行严格安全审计
    audit_staged_files(STAGE_DIR)

    # 4. 生成 ZIP 压缩包
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

    # 5. 清理暂存区
    shutil.rmtree(STAGE_DIR.parent, ignore_errors=True)

    elapsed = time.time() - start_time
    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print("\n==================================================")
    print(f"[SUCCESS] 云端部署纯净源码包打包成功！")
    print(f"产物路径: {OUTPUT_ZIP}")
    print(f"压缩包体积: {zip_size_mb:.1f} MB")
    print(f"耗时: {elapsed:.1f} 秒")
    print("==================================================")

if __name__ == "__main__":
    main()
