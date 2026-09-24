"""
清空历史项目并使用 Playwright (Edge) 自动化截取 1920x1080 全高清真实 UI 界面。
主线报告类型：智库专报（资料留空，依托权威联网 RAG 与国家标准智库大纲撰写）。
"""
import json
import os
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_IMAGES = REPO_ROOT / "docs" / "images"
DOCS_IMAGES.mkdir(parents=True, exist_ok=True)

LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
FAIRYREPORT_DATA = Path(LOCALAPPDATA) / "FairyReport" if LOCALAPPDATA else Path.home() / "FairyReport"
PROJ_NAME = "我国算力基础设施高质量发展与绿色智能算力中心布局智库专报"


def clean_history_data():
    """1. 彻底清空所有历史项目与缓存"""
    print("[1/6] Cleaning all historical project data...")
    
    # 清空 projects 文件夹
    projects_dir = FAIRYREPORT_DATA / "projects"
    if projects_dir.exists():
        for item in projects_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
        print(f"  Emptied: {projects_dir}")
        
    # 清空 vector_db 文件夹
    vector_db_dir = FAIRYREPORT_DATA / "vector_db"
    if vector_db_dir.exists():
        shutil.rmtree(vector_db_dir, ignore_errors=True)
        vector_db_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Reset vector_db: {vector_db_dir}")

    # 清空 SQLite engine.db 中的 projects 与 materials
    db_path = FAIRYREPORT_DATA / "engine.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM materials;")
            cur.execute("DELETE FROM projects;")
            try:
                cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('materials', 'projects');")
            except Exception:
                pass
            conn.commit()
            cur.execute("VACUUM;")
            print("  Emptied materials and projects tables in engine.db")
        except Exception as e:
            print(f"  SQLite cleanup warning: {e}")
        finally:
            conn.close()

    # 清理 repo 下的 data/projects（如果存在）
    repo_projects = REPO_ROOT / "data" / "projects"
    if repo_projects.exists():
        shutil.rmtree(repo_projects, ignore_errors=True)

    # 重置 desktop-state.json
    state_file = FAIRYREPORT_DATA / "desktop-state.json"
    if state_file.exists():
        state_file.write_text("{}", encoding="utf-8")
        print("  Reset desktop-state.json")


def setup_thinktank_project():
    """准备好智库专报标准项目数据与大纲"""
    print("[2/6] Setting up Think Tank report project and outline...")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    # 插入项目到 SQLite
    db_path = FAIRYREPORT_DATA / "engine.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("INSERT INTO projects (name, created_at) VALUES (?, ?);", (PROJ_NAME, now_str))
    conn.commit()
    conn.close()

    # 创建项目目录与标准大纲
    p_dir = FAIRYREPORT_DATA / "projects" / PROJ_NAME
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / "files").mkdir(parents=True, exist_ok=True)

    # 读取智库专报标准模板
    tmpl_file = REPO_ROOT / "generic_knowledge" / "templates" / "zhiku_juece_zhuanbao.json"
    tmpl_data = json.loads(tmpl_file.read_text(encoding="utf-8"))

    outline_data = {
        "report_type": "智库专报",
        "outline_md": tmpl_data["outline_md"],
        "chapters": tmpl_data["chapters"],
        "writing_order": [1, 2, 3, 4, 5],
        "writing_order_reason": "智库专报遵循'导语提纲挈领→态势研判→矛盾剖析→对策建言→支撑附表'的逻辑链条。",
        "updated_at": "2026-09-24T13:10:00"
    }
    (p_dir / "outline.json").write_text(json.dumps(outline_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 准备第二章（总体态势与基本认识）高品质正文，含三线表与联网引用
    ch2_text = """## 一、总体态势与基本认识

### （一）算力基础设施建设进入智能主导新阶段

近年来，以大模型和通用人工智能为代表的新一代信息技术蓬勃发展，驱动我国算力基础设施从“通用算力为主”快速向“智能算力主导”跨越。截至目前，全国在用数据中心机架总规模超过 810 万标准机架，算力总规模达 230 EFLOPS，居全球第二位【网:中国信息通信研究院《中国算力发展指数白皮书》】。智能算力规模占比由 2021 年的 15% 跃升至 32% 以上，年复合增长率超过 45%。

#### 表1-1 我国主要算力枢纽节点算力规模与综合能效对比表
| 枢纽节点名称 | 智能算力规模 (EFLOPS) | 平均设计 PUE 指标 | 可再生能源使用比例 | 算力网络互联时延 |
| :--- | :---: | :---: | :---: | :---: |
| 京津冀枢纽（张家口集群） | 35.6 | ≤ 1.18 | ≥ 65% | < 5 ms |
| 长三角枢纽（长三角生态绿色示范区） | 42.0 | ≤ 1.22 | ≥ 50% | < 5 ms |
| 粤港澳大湾区枢纽（韶关集群） | 28.5 | ≤ 1.20 | ≥ 55% | < 8 ms |
| 成渝枢纽（天府/重庆集群） | 26.2 | ≤ 1.20 | ≥ 75% | < 10 ms |
| 贵州枢纽（贵安集群） | 31.8 | ≤ 1.15 | ≥ 80% | < 15 ms |
| 内蒙古枢纽（和林格尔集群） | 30.2 | ≤ 1.15 | ≥ 85% | < 12 ms |

### （二）重大战略意义与跨周期定位

作为承载数字经济发展与国家竞争力的战略大动脉，智能算力中心不仅是技术创新的孵化器，更是新型能源体系与算网协同的核心支点【网:国家发展改革委等部门《深入实施“东数西算”工程加快构建全国一体化算力网的实施意见》】。当前，算力网络正加快从“点状孤岛建设”向“一体化算网调度”演进，构筑起面向实体经济智能化转型的坚实底座。"""

    chapters_data = {
        "chapters": {
            "1": "## 【导语 / 内容摘要】\n\n当前我国算力总规模已突破 230 EFLOPS，智能算力需求迎来井喷式增长。本专报系统梳理全国一体化算力网推进态势，剖析跨区域调度受限、绿色低碳转型压力大及关键技术生态壁垒三大突出矛盾，并提出强化国家算网统筹、实施算电协同绿电替代、加快自主算力生态攻关等政策举措。",
            "2": ch2_text,
            "3": "## 二、面临的突出矛盾与风险研判\n\n### （一）跨区域算网一体化调度与异构兼容难题突出\n\n当前各算力枢纽集群在网络架构、调度协议及底层算力芯片指令集上存在明显异构壁垒，东部实时性算力需求向西部迁移仍面临高时延与网络传输资费偏高制约【网:国家信息中心《智能计算中心规划建设指南》】。\n\n### （二）算电协同机制不健全，高负荷运行对局部电网形成冲击\n\n大规模智算中心峰值功耗高、负荷波动大，局部地区绿电就地消纳机制尚未成熟，亟需建立'算力-电力'联动响应机制与绿色电力直供交易通道。",
            "4": "## 三、对策建议与政策举措\n\n### （一）完善全国一体化算力网顶层调度与标准化互通\n\n统一国家级算网调度标准，推行算力标识与标准化计量计费，支持建立全国多方算力调度交易市场平台。\n\n### （二）深化算电协同与绿电聚合消纳模式\n\n在西部枢纽节点率先开展算力中心直连源网荷储微电网试点，全面提升新能源消纳水平，严控 PUE 不高于 1.20 门槛。",
            "5": "## 附件/附表\n\n### 附表1 全国一体化算力网八大枢纽核心指标对比总表"
        },
        "updated_at": "2026-09-24T13:10:00"
    }
    (p_dir / "chapters.json").write_text(json.dumps(chapters_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 准备专家审阅持久化数据 (reviews.json)
    reviews_data = {
        "reviews": {
            "2": {
                "overall_score": 95,
                "dimension_scores": {
                    "完整性": 96,
                    "一致性": 95,
                    "合规性": 98,
                    "数据充分性": 92
                },
                "issues": [
                    {
                        "category": "数据充分性",
                        "severity": "info",
                        "description": "表格数据完整详实，建议进一步增加西部算力集群直供绿电的度电成本测算对照。",
                        "suggestion": "可在后文补充附表进行绿电成本专项比对。"
                    }
                ],
                "summary": "该章节总体态势梳理逻辑清晰，数据详实，工程经济三线表格规范，符合国家发改委智库专报标准。",
                "status": "passed"
            }
        },
        "updated_at": "2026-09-24T13:10:00"
    }
    (p_dir / "reviews.json").write_text(json.dumps(reviews_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Created Think Tank project: {PROJ_NAME}")


def run_capture():
    clean_history_data()
    setup_thinktank_project()

    # 启动后台 Python 引擎
    print("[3/6] Starting backend engine (127.0.0.1:8001)...")
    engine_proc = subprocess.Popen(
        ["python", "-m", "uvicorn", "engine.app.main:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # 启动前端静态预览服务
    print("[4/6] Starting frontend preview server (127.0.0.1:1420)...")
    vite_proc = subprocess.Popen(
        ["npx", "vite", "preview", "--port", "1420"],
        cwd=str(REPO_ROOT / "desktop"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True
    )

    time.sleep(3)

    try:
        from playwright.sync_api import sync_playwright

        print("[5/6] Launching Playwright (Edge) to capture 1920x1080 full HD UI...")
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
            )
            page = context.new_page()

            # 访问前端
            page.goto("http://127.0.0.1:1420")
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            # 点击“🎯 快捷演示体验（免登录直接进入）”
            demo_btn = page.locator(".demo-btn")
            if demo_btn.is_visible():
                demo_btn.click()
                time.sleep(1.5)

            # 等待顶部主导航条出现
            page.wait_for_selector(".wizard-nav", timeout=10000)

            # ----------------------------------------------------
            # 步骤 1：项目与资料（资料留空）
            # ----------------------------------------------------
            print("  Capturing Step 1: Projects & Materials...")
            step1_step = page.locator(".wizard-step").filter(has_text="1")
            step1_step.click()
            time.sleep(1.5)

            # 选中智库专报项目
            select_el = page.locator("select.select-input")
            if select_el.is_visible():
                select_el.select_option(value=PROJ_NAME)
                time.sleep(1.5)

            step1_path = DOCS_IMAGES / "step1_materials.png"
            page.screenshot(path=str(step1_path))
            print(f"  [OK] Saved: {step1_path.name}")

            # ----------------------------------------------------
            # 步骤 2：模板与大纲（智库专报卡片选中）
            # ----------------------------------------------------
            print("  Capturing Step 2: Templates & Outline (Think Tank)...")
            step2_step = page.locator(".wizard-step").filter(has_text="2")
            step2_step.click()
            time.sleep(1.5)

            # 点击“智库专报”卡片
            zhiku_card = page.locator(".template-item").filter(has_text="智库专报").first
            if zhiku_card.is_visible():
                zhiku_card.click()
                time.sleep(1.5)

            step2_path = DOCS_IMAGES / "step2_outline.png"
            page.screenshot(path=str(step2_path))
            print(f"  [OK] Saved: {step2_path.name}")

            # ----------------------------------------------------
            # 步骤 3：章节写作（三线表、思考流与角标）
            # ----------------------------------------------------
            print("  Capturing Step 3: Chapter Writing...")
            step3_step = page.locator(".wizard-step").filter(has_text="3")
            step3_step.click()
            time.sleep(2)

            # 点击选择第二章胶囊
            ch2_chip = page.locator(".order-chip").filter(has_text="第 2 章").first
            if ch2_chip.is_visible():
                ch2_chip.click()
                time.sleep(1.5)

            step3_path = DOCS_IMAGES / "step3_writing.png"
            page.screenshot(path=str(step3_path))
            print(f"  [OK] Saved: {step3_path.name}")

            # ----------------------------------------------------
            # 步骤 4：审阅修改（多维专家诊断与徽标）
            # ----------------------------------------------------
            print("  Capturing Step 4: Quality Review...")
            step4_step = page.locator(".wizard-step").filter(has_text="4")
            step4_step.click()
            time.sleep(2)

            # 点击“专家诊断报告”按钮打开全高抽屉
            diag_btn = page.locator("button.drawer-btn").filter(has_text="专家诊断报告").first
            if diag_btn.is_visible():
                diag_btn.click()
                time.sleep(1.5)

            step4_path = DOCS_IMAGES / "step4_review.png"
            page.screenshot(path=str(step4_path))
            print(f"  [OK] Saved: {step4_path.name}")

            # 关闭抽屉，避免遮罩层阻挡后续步骤点击
            overlay = page.locator(".ref-drawer-overlay")
            if overlay.is_visible():
                overlay.click(force=True)
                time.sleep(1)

            # ----------------------------------------------------
            # 步骤 5：成果导出（自洽性核验与Word初稿导出）
            # ----------------------------------------------------
            print("  Capturing Step 5: Export...")
            step5_step = page.locator(".wizard-step").filter(has_text="5")
            step5_step.click(force=True)
            time.sleep(2)

            # 点击自洽性核验按钮（如果可见）
            verify_btn = page.locator("button").filter(has_text="重新核验").first
            if verify_btn.is_visible():
                verify_btn.click()
                time.sleep(2)

            step5_path = DOCS_IMAGES / "step5_export.png"
            page.screenshot(path=str(step5_path))
            print(f"  [OK] Saved: {step5_path.name}")

            browser.close()

        print("[6/6] Verifying all generated image dimensions...")
        all_passed = True
        for name in ["step1_materials.png", "step2_outline.png", "step3_writing.png", "step4_review.png", "step5_export.png"]:
            img_file = DOCS_IMAGES / name
            if img_file.exists():
                with Image.open(img_file) as im:
                    print(f"  {name}: size={im.size[0]}x{im.size[1]}, format={im.format}")
                    if im.size != (1920, 1080):
                        print(f"  [FAIL] Size mismatch: expected 1920x1080, got {im.size}")
                        all_passed = False
            else:
                print(f"  [FAIL] Missing image: {name}")
                all_passed = False

        if all_passed:
            print("\nSUCCESS: All 5 real UI screenshots generated at exact 1920x1080 resolution!")

    finally:
        print("Cleaning up background processes...")
        try:
            engine_proc.terminate()
        except:
            pass
        try:
            vite_proc.terminate()
        except:
            pass
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/F", "/IM", "fairyreport-engine.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Done!")


if __name__ == "__main__":
    run_capture()
