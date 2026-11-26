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
    target_root = os.path.join(repo_root, "desktop", "src-tauri", "target")
    release_candidates = [
        os.path.join(target_root, "release"),
        os.path.join(target_root, "x86_64-pc-windows-gnu", "release"),
        os.path.join(target_root, "x86_64-pc-windows-msvc", "release"),
    ]
    valid_releases = [
        d for d in release_candidates
        if os.path.exists(os.path.join(d, "fairyreport-desktop.exe"))
    ]
    if not valid_releases:
        raise RuntimeError("未找到 fairyreport-desktop.exe，请先编译 Tauri Release！")
    target_release = max(
        valid_releases,
        key=lambda d: os.path.getmtime(os.path.join(d, "fairyreport-desktop.exe")),
    )
    print(f"  使用最新桌面端 Release 目录：{target_release}")
    
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
    # GNU 工具链动态链接 WebView2Loader.dll（MSVC 静态链接时不存在），有则必拷
    webview2_dll = os.path.join(target_release, "WebView2Loader.dll")
    if os.path.exists(webview2_dll):
        shutil.copy2(webview2_dll, os.path.join(stage_dir, "WebView2Loader.dll"))
        print("  已拷贝 WebView2Loader.dll")
    # cdylib 只在部分目标上生成，Windows 桌面运行不需要它：有就拷，没有就跳过
    lib_dll = os.path.join(target_release, "fairyreport_desktop_lib.dll")
    if os.path.exists(lib_dll):
        shutil.copy2(lib_dll, os.path.join(stage_dir, "fairyreport_desktop_lib.dll"))
    else:
        print("  提示：未找到 fairyreport_desktop_lib.dll（Windows 运行不需要），已跳过")

    engine_candidates = [
        os.path.join(repo_root, "desktop", "src-tauri", "binaries", "fairyreport-engine-x86_64-pc-windows-msvc.exe"),
        os.path.join(repo_root, "desktop", "src-tauri", "binaries", "fairyreport-engine-x86_64-pc-windows-gnu.exe"),
        os.path.join(target_release, "fairyreport-engine.exe"),
    ]
    valid_engines = [
        p for p in engine_candidates
        if os.path.exists(p) and os.path.getsize(p) > 10 * 1024 * 1024
    ]
    if not valid_engines:
        raise RuntimeError("未找到有效的独立后端引擎二进制 (fairyreport-engine.exe 体积需 > 10MB)，请先运行 scripts/build_engine.py！")
    engine_src = max(valid_engines, key=os.path.getmtime)
    print(f"  使用最新后端引擎二进制：{engine_src}")
    shutil.copy2(
        engine_src,
        os.path.join(stage_dir, "fairyreport-engine.exe")
    )

    # 校验桌面主程序体积
    desktop_exe = os.path.join(stage_dir, "FairyReport.exe")
    if not os.path.exists(desktop_exe) or os.path.getsize(desktop_exe) < 1 * 1024 * 1024:
        raise RuntimeError("FairyReport.exe 不存在或体积异常 (< 1MB)，请先编译 Tauri Release！")

    # 拷贝离线快速向量模型 data/fastembed_models（若存在），使接收方上传底稿时 100% 离线秒级向量化
    model_src = os.path.join(repo_root, "data", "fastembed_models")
    if os.path.exists(model_src) and os.path.exists(os.path.join(model_src, "model_optimized.onnx")):
        print("  拷贝离线向量嵌入模型 data/fastembed_models/ ...")
        shutil.copytree(
            model_src,
            os.path.join(stage_dir, "data", "fastembed_models"),
            dirs_exist_ok=True,
        )
    
    # 拷贝 15 类报告专属 Word 模板包
    pattern_src = os.path.join(repo_root, "pattern")
    if os.path.exists(pattern_src):
        shutil.copytree(pattern_src, os.path.join(stage_dir, "pattern"), dirs_exist_ok=True)

    # 拷贝 15 类报告内置 JSON 大纲模板包（开箱即用，无需云端同步）
    templates_src = os.path.join(repo_root, "generic_knowledge", "templates")
    if os.path.exists(templates_src):
        shutil.copytree(
            templates_src,
            os.path.join(stage_dir, "generic_knowledge", "templates"),
            dirs_exist_ok=True,
        )

    # 拷贝使用说明：指南 Word/Markdown 版与 MCP 接入指南
    guide_dir = os.path.join(stage_dir, "使用说明")
    os.makedirs(guide_dir, exist_ok=True)
    for src_name, dst_name in (
        ("FairyReport_快速上手操作指南.docx", "FairyReport_快速上手操作指南.docx"),
        ("FairyReport_用户操作手册.docx", "FairyReport_用户操作手册.docx"),
        ("BEGINNER_GUIDE.md", "BEGINNER_GUIDE.md"),
        ("USER_GUIDE.md", "USER_GUIDE.md"),
        ("MCP_GUIDE.md", "MCP接入指南.md"),
    ):
        src = os.path.join(repo_root, "docs", src_name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(guide_dir, dst_name))
        else:
            print(f"  提示：未找到 {src}，已跳过")

    # 更新历史（与 Release / 网站同一份来源）
    changelog = os.path.join(repo_root, "CHANGELOG.md")
    if os.path.exists(changelog):
        shutil.copy2(changelog, os.path.join(guide_dir, "更新历史.md"))
    else:
        print(f"  提示：未找到 {changelog}，已跳过")

    readme_text = f"""FairyReport 智能报告编制应用 & MCP Server (v{version} 绿色免安装便携版)
======================================================================

【方式一：独立桌面工作台快速启动】
1. 解压本压缩包至任意磁盘文件夹（例如 D:\\Tools\\FairyReport）。
2. 双击运行「FairyReport.exe」即可直接进入五步编制工作台（免注册、免登录、完全免费使用）。
   （首次启动时若出现 Windows Defender 安全拦截提示，点击“更多信息” -> “仍要运行”即可）

【模型与 API Key 设置（支持国内外主流厂商）】
1. 进入工作台后，点击右上角「设置」按钮。
2. 原生支持国内外主流大模型接口：
   - 国内平台：DeepSeek、通义千问（DashScope）、Kimi（Moonshot）、硅基流动（SiliconFlow）等；
   - 国际平台：OpenAI（GPT 系列）、Anthropic Claude（原生 /v1/messages）、Google Gemini、OpenRouter 等。
3. 填入 Base URL 与 API Key 后（仅保存在您本地，绝不上云），点击「🔄 获取最新模型」即可动态拉取厂商最新模型列表，或手动填写任意自定义模型 ID。

【方式二：零 Python 环境接入 MCP Server（供桌面端 AI Agent 调用）】
本便携包内的 fairyreport-engine.exe 已内置标准 MCP Server，无需安装 Python 或任何依赖，
即可直接挂载到 Cherry Studio、Claude Desktop / Cowork、Trae、Cursor、Windsurf、Antigravity 等客户端
（默认零额外 API Key，由客户端自带大模型负责推理写作）：

1. STDIO 挂载配置示例（将路径替换为您实际解压目录）：
   {{
     "mcpServers": {{
       "fairyreport": {{
         "command": "D:/Tools/FairyReport/fairyreport-engine.exe",
         "args": ["--mcp"]
       }}
     }}
   }}
2. Streamable HTTP 模式启动命令（适合 OpenClaw / 远程网关挂载）：
   fairyreport-engine.exe --mcp --transport streamable-http --port 8002
3. 便携数据互通：因同级存在 .portable 标记，MCP 模式会自动读写本目录下的 data\\ 文件夹，
   直接复用包内离线向量模型（data\\fastembed_models\\），并与 FairyReport.exe 桌面端共享项目数据。

【使用说明文档】
本包内「使用说明」文件夹含：
- 《快速上手操作指南》与《用户操作手册》Word 版（.docx）及 Markdown 源文件；
- MCP接入指南.md：各主流 AI Agent 客户端配置教程与对话指令示例；
- 更新历史.md：本软件的版本更新记录。

【核心安全与便携特性】
1. 纯本地物理隔离：15 类专业报告模板、工程底稿、解析切片、向量索引与编制成果 100% 封闭保存在本机，物理隔离、零数据上云。
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
