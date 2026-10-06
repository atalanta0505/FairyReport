"""
打包绿色便携版 dist/FairyReport-Local-v<version>-Windows-x64.zip
版本号取自 desktop/package.json，避免多处硬编码漂移。
"""
import json
import os
import shutil
import zipfile
import time

def main():
    start = time.time()
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo_root, "desktop", "package.json"), encoding="utf-8") as f:
        version = json.load(f)["version"]
    dist_dir = os.path.join(repo_root, "dist")
    target_release = os.path.join(repo_root, "desktop", "src-tauri", "target", "release")
    
    stage_dir = os.path.join(dist_dir, f"FairyReport-Local-v{version}-Windows-x64")
    if os.path.exists(stage_dir):
        shutil.rmtree(stage_dir, ignore_errors=True)
    
    os.makedirs(os.path.join(stage_dir, "data"), exist_ok=True)
    with open(os.path.join(stage_dir, ".portable"), "w") as f:
        pass
        
    shutil.copy2(
        os.path.join(target_release, "fairyreport-desktop.exe"),
        os.path.join(stage_dir, "FairyReport.exe")
    )
    # cdylib 只在部分目标上生成，Windows 桌面运行不需要它：有就拷，没有就跳过
    lib_dll = os.path.join(target_release, "fairyreport_desktop_lib.dll")
    if os.path.exists(lib_dll):
        shutil.copy2(lib_dll, os.path.join(stage_dir, "fairyreport_desktop_lib.dll"))
    else:
        print("  提示：未找到 fairyreport_desktop_lib.dll（Windows 运行不需要），已跳过")
    shutil.copy2(
        os.path.join(target_release, "fairyreport-engine.exe"),
        os.path.join(stage_dir, "fairyreport-engine.exe")
    )
    
    # 拷贝 15 类报告专属 Word 模板包
    pattern_src = os.path.join(repo_root, "pattern")
    if os.path.exists(pattern_src):
        shutil.copytree(pattern_src, os.path.join(stage_dir, "pattern"), dirs_exist_ok=True)

    # 拷贝使用说明：两份指南的 Word 版与 Markdown 源文件
    guide_dir = os.path.join(stage_dir, "使用说明")
    os.makedirs(guide_dir, exist_ok=True)
    for name in (
        "FairyReport_快速上手操作指南.docx",
        "FairyReport_用户操作手册.docx",
        "BEGINNER_GUIDE.md",
        "USER_GUIDE.md",
    ):
        src = os.path.join(repo_root, "docs", name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(guide_dir, name))
        else:
            print(f"  提示：未找到 {src}，已跳过")

    # 更新历史（与 Release / 网站同一份来源）
    changelog = os.path.join(repo_root, "CHANGELOG.md")
    if os.path.exists(changelog):
        shutil.copy2(changelog, os.path.join(guide_dir, "更新历史.md"))
    else:
        print(f"  提示：未找到 {changelog}，已跳过")

    readme_text = f"""FairyReport 智能报告编制应用 (v{version} 本地安全专业版)
==================================================

【快速启动】
1. 解压本压缩包至任意磁盘文件夹（例如 D:\\Tools\\FairyReport）。
2. 双击运行「FairyReport.exe」即可直接启动工作台。
   （首次启动时若出现 Windows Defender 安全拦截提示，点击“更多信息” -> “仍要运行”即可）

【免登录体验】
在登录界面底部点击「🎯 快捷演示体验（免登录直接进入）」按钮，即可免登录直接进入编制工作台。

【模型与 API Key 设置】
1. 进入工作台后，点击右上角「⚙️ 设置」图标。
2. 基础地址（Base URL）：默认已配置官方规范 https://api.deepseek.com。
3. API Key：填入您在 DeepSeek 开放平台申请的 API Key（系统仅保存在您本地，绝不上云）。
4. 模型选择：默认推荐 deepseek-flash（高性价比、流式响应极速），亦可点击「🔄 获取最新模型」动态拉取官方最新模型列表。

【使用说明文档】
本包内「使用说明」文件夹含：
- 《快速上手操作指南》与《用户操作手册》Word 版（.docx）及 Markdown 源文件；
- 更新历史.md：本软件的版本更新记录。

【核心安全与便携特性】
1. 纯本地物理隔离：工程底稿、解析切片、向量索引与编制成果 100% 封闭保存在本机的 data/ 目录中，物理隔离、零数据上云。
2. 绿色免安装（.portable）：本便携包完全自包含，不写 Windows 注册表，无需预装 Python、Rust 或 NodeJS，解压即用、随 U 盘即插即用。
3. 纯净发布：本安装包为完全纯净空白模板，无任何历史项目数据或开发缓存，放心分发。
"""
    with open(os.path.join(stage_dir, "使用说明.txt"), "w", encoding="utf-8") as f:
        f.write(readme_text)

    zip_path = os.path.join(dist_dir, f"FairyReport-Local-v{version}-Windows-x64.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    print(f"开始压缩至 {zip_path}...")
    # 使用 ZIP_DEFLATED 压缩（压缩级别 1 追求最快速度）
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        for root, dirs, files in os.walk(stage_dir):
            for d in dirs:
                dir_full = os.path.join(root, d)
                dir_rel = os.path.relpath(dir_full, dist_dir).replace("\\", "/") + "/"
                zf.writestr(dir_rel, "")
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, dist_dir).replace("\\", "/")
                zf.write(full_path, rel_path)
                
    shutil.rmtree(stage_dir, ignore_errors=True)
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"打包完成！文件大小: {size_mb:.1f} MB，耗时: {time.time() - start:.1f} 秒")

if __name__ == "__main__":
    main()
