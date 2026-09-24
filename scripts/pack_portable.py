"""
打包绿色便携版 FairyReport-Local-v1.5.0-Windows-x64.zip
"""
import os
import shutil
import zipfile
import time

def main():
    start = time.time()
    repo_root = r"D:\Repo\FairyReport_lite"
    dist_dir = os.path.join(repo_root, "dist")
    target_release = os.path.join(repo_root, "desktop", "src-tauri", "target", "release")
    
    stage_dir = os.path.join(dist_dir, "FairyReport-Local-v1.5.0-Windows-x64")
    if os.path.exists(stage_dir):
        shutil.rmtree(stage_dir, ignore_errors=True)
    
    os.makedirs(os.path.join(stage_dir, "data"), exist_ok=True)
    with open(os.path.join(stage_dir, ".portable"), "w") as f:
        pass
        
    shutil.copy2(
        os.path.join(target_release, "fairyreport-desktop.exe"),
        os.path.join(stage_dir, "FairyReport.exe")
    )
    shutil.copy2(
        os.path.join(target_release, "fairyreport_desktop_lib.dll"),
        os.path.join(stage_dir, "fairyreport_desktop_lib.dll")
    )
    shutil.copy2(
        os.path.join(target_release, "fairyreport-engine.exe"),
        os.path.join(stage_dir, "fairyreport-engine.exe")
    )
    
    readme_text = """FairyReport 本地安全专业版 (v1.5.0)
==================================================

【快速启动】
双击运行「FairyReport.exe」即可启动系统。

【核心特性】
1. 纯本地物理隔离引擎：工程底稿、报告内容 100% 封闭在本地电脑，物理隔离、零数据上云。
2. 绿色免安装：本软件已开启便携模式（.portable），所有运行时数据和项目文件均存放在同级 data/ 目录中，不污染系统注册表。
3. 认证中心：默认连接 http://101.42.9.223（仅用于账号认证与行业通用规范模板更新）。

【免登录体验】
在登录界面点击下方「🎯 快捷演示体验（免登录直接进入）」按钮，即可直接进入系统体验全部功能。
"""
    with open(os.path.join(stage_dir, "使用说明.txt"), "w", encoding="utf-8") as f:
        f.write(readme_text)

    zip_path = os.path.join(dist_dir, "FairyReport-Local-v1.5.0-Windows-x64.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    print(f"开始压缩至 {zip_path}...")
    # 使用 ZIP_DEFLATED 压缩（压缩级别 1 追求最快速度）
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        for root, dirs, files in os.walk(stage_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, dist_dir)
                zf.write(full_path, rel_path)
                
    shutil.rmtree(stage_dir, ignore_errors=True)
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"打包完成！文件大小: {size_mb:.1f} MB，耗时: {time.time() - start:.1f} 秒")

if __name__ == "__main__":
    main()
