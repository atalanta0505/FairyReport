"""
FairyReport v1.0.5 - Global Configuration
"""
import os
from pathlib import Path

# ── Project paths ──
import sys as _sys

def _get_base_dir() -> Path:
    """Return the writable data root directory.

    After packaging, _MEIPASS is a read-only temp directory (code, templates, static assets);
    writable data lives in the user data directory (FRL_DATA_DIR env var or %LOCALAPPDATA%/FairyReport).
    """
    env_data = os.environ.get("FRL_DATA_DIR")
    if env_data:
        return Path(env_data)
    if getattr(_sys, 'frozen', False):
        return Path(_sys._MEIPASS)
    return Path(__file__).parent

def _get_resource_dir() -> Path:
    """Return the read-only resource root directory (_MEIPASS after packaging, PROJECT_ROOT in dev)."""
    if getattr(_sys, 'frozen', False):
        return Path(_sys._MEIPASS)
    return Path(__file__).parent

PROJECT_ROOT = _get_resource_dir()
RESOURCE_DIR = PROJECT_ROOT  # Read-only resource directory
DATA_ROOT = _get_base_dir()  # Writable data directory (user data dir after packaging)

# Generic knowledge base files (read-only resources)
GENERIC_KB_DIR = RESOURCE_DIR / "generic_knowledge"
# Generic vector database — writable
GENERIC_DB_DIR = DATA_ROOT / "data/vector_db/generic"
# Project data (materials, chapters, reports) — writable
PROJECTS_DIR = DATA_ROOT / "data/projects"

# ── LLM configuration ──
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"  # SDK requires the /v1 suffix internally

# ── Embedding model ──
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# ── Document parsing & chunking ──
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# ── RAG retrieval ──
RAG_RESULTS_PER_SOURCE = 5  # Number of items retrieved per knowledge base (project/generic)
RERANK_ENABLED = False      # Whether to enable Rerank (requires SiliconFlow API)
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"  # Rerank model
RERANK_BASE_URL = "https://api.siliconflow.cn/v1/rerank"

# ── LLM temperature ──
TEMPERATURE_OUTLINE = 0.2
TEMPERATURE_ORDER = 0.1
TEMPERATURE_HINT = 0.3
TEMPERATURE_WRITING = 0.2
TEMPERATURE_MODIFY = 0.2

# ── API penalty parameters (suppress repetition, reduce length) ──
FREQUENCY_PENALTY = 0.4     # Suppress synonymous repetition / filler phrasing
PRESENCE_PENALTY = 0.25     # Avoid repeatedly using the same sentence patterns
TOP_P = 0.85                # Nucleus sampling, cut low-probability filler tokens

# ── Report types & word limits (per 《Decision Evaluation 2024》 12 types of pre-investment consulting deliverables) ──
REPORT_TYPES = [
    "产业发展规划报告",
    "企业发展规划报告",
    "园区发展规划报告",
    "投资机会研究报告",
    "初步可行性研究报告",
    "项目建议书",
    "可行性研究报告",
    "项目申请书(报告)",
    "资金申请报告",
    "社会评价报告",
    "后评价报告",
    "政府和社会资本合作项目特许经营方案",
    "项目评估报告",
    "专题研究报告",
]

# ═══════════════════════════════════════════════════════════════
# Technical analysis constants (v1.0.4)
# ═══════════════════════════════════════════════════════════════

# Report types where technical analysis is always enabled
TECH_ANALYSIS_ALWAYS_REPORT_TYPES = [
    "可行性研究报告",
    "初步可行性研究报告",
    "项目申请书(报告)",
    "项目评估报告",
]

# Report types where technical analysis is conditionally enabled (when topic involves tech)
TECH_ANALYSIS_CONDITIONAL_REPORT_TYPES = [
    "专题研究报告",
    "产业发展规划报告",
    "园区发展规划报告",
    "企业发展规划报告",
]

# Chapter keywords that trigger technical analysis enhancement
TECH_CHAPTER_KEYWORDS = [
    "技术方案", "建设方案", "设备方案", "工程方案",
    "数字化方案", "工艺", "产品方案", "资源能源",
    "技术路线", "工艺路线", "设备选型", "能耗",
    "节能减排", "环保", "安全", "生产方案",
    "施工方案", "布置方案",
]

# Technical analysis review system prompt (for review phase)
TECH_REVIEW_SYSTEM_PROMPT = """\
你是工程咨询技术分析审校专家。请对以下章节进行技术分析质量专项校核。

校核维度（逐项检查）：
1. **路线完整性**：是否列出2个以上可比技术路线或方案？若无，是否有明确说明不适用比选的原因？
2. **指标颗粒度**：是否有"先进、可靠、经济"等抽象词而未给出具体指标类型（产能、能耗、占地、投资、排放、国产化率等）？是否区分"已有数据"和"待核实数据"？
3. **项目约束绑定**：推荐理由是否结合了规模、场地、投资、工期、运维、标准等具体项目条件？
4. **资料依据**：关键判断是否有来源标注或资料边界说明？
5. **风险识别**：是否涉及技术来源、设备供应、实施难度、运维能力、安全环保等风险？是否有控制措施？
6. **资料不足声明**：资料缺失时，是否仍给出了确定性的结论？
7. **套话压制**：是否存在无支撑的"成熟可靠、国内领先、经济合理、节能环保"等空泛表述？

输出格式（严格遵守）：
```
【校核结果】通过 / 需补充 / 不适用

【原因说明】（简短说明判定理由）

【校核详情】
（逐项列出检查问题和发现的问题，通过的项也需简要确认）

【修改建议】
（逐条给出具体可执行的修改建议，不是泛泛评价）

【需补充资料清单】（仅当结果为"需补充"时输出）
- 项目规模：...
- 技术路线：...
- 设备参数：...
- 指标约束：...
- 建设条件：...
- 投资约束：...
- 依据材料：...
```

判定标准：
- **通过**：至少有路线识别、关键指标、推荐理由和风险控制；资料边界表达清楚。
- **需补充**：章节方向正确，但缺少关键资料、指标、依据或项目约束绑定。
- **不适用**：该章节不涉及技术方案、设备方案、工程方案、工艺路线或资源能源技术判断。
"""

# Technical analysis writing framework (injected into writing prompt for tech chapters)
TECH_WRITING_FRAMEWORK = """\
## 技术分析写作框架（本章适用）

本章涉及技术分析内容，请按以下框架组织论证（不强制新增小节标题，在现有标题下嵌入即可）：

1. **项目技术问题识别**：说明本章需要解决的核心技术问题（处理能力、工艺适配、设备匹配、建设条件、能耗排放、安全可靠性等）。
2. **主流技术路线或备选方案**：列出2-3个可比方案；若资料不足，说明这些方案为通用备选路线，不代表最终推荐。
3. **关键技术指标**：围绕产能、效率、能耗、占地、投资强度、运行成本、排放、自动化、国产化率、安全等级、维护周期等建立指标表。**无具体数值时标注"待补充/待核实"，不得编造精确数据。**
4. **多方案比选**：结合项目条件比较，不只比较抽象优缺点；优先用表格呈现适用场景、优势、限制和风险。
5. **推荐方案及适用条件**：有足够资料时给出推荐方案并说明理由；资料不足时给出阶段性倾向、待核实条件和后续论证事项。
6. **技术风险与控制措施**：识别技术来源、设备供应、标准合规、实施难度、运维能力、知识产权、安全环保等风险，提出控制措施。
7. **需补充资料**：列明影响最终判断的资料缺口。

## 资料不足场景输出规则

当以下关键条件缺失时，**不得输出无条件推荐或确定性结论**：
- 缺少建设规模 → 按常见规模区间做框架性比较，提示补充设计规模
- 缺少设备参数 → 列出关键设备类别和应核实参数（处理能力、功率、效率等），不得编造型号
- 缺少投资约束 → 说明需结合投资上限、运行成本、全寿命周期成本进行复核，不得仅以"经济合理"推荐
- 缺少能耗排放要求 → 列出应核实的单位能耗、排放标准、碳排放强度等指标，不得泛称"绿色低碳"
- 缺少已有倾向方案 → 分别说明可选路线的适用条件，将推荐结论表述为"待补充资料后确定"

## 套话压制规则

以下空泛表述**禁止孤立使用**，必须后附指标、依据或限制条件：
- "成熟可靠" → 改为具体说明成熟度来源、应用案例数量或可靠性指标
- "国内领先" → 改为与行业标准或同类项目的具体对标数据，或标注"待核实"
- "经济合理" → 改为结合投资约束和运行成本的说明，或标注"需结合投资上限复核"
- "绿色低碳"/"节能环保" → 改为列出应核实的能耗指标、排放标准、碳强度，不得泛泛而论
- "先进适用" → 改为从具体指标维度（效率、能耗、占地、自动化等）进行比较
"""

# Data insufficiency self-check rules (injected into writing prompt for tech chapters)
TECH_INSUFFICIENT_DATA_RULES = """\
## 资料不足判定

在输出推荐结论前，请自查以下资料条件是否满足：
1. 建设规模/服务能力 → 是否明确？
2. 技术路线/工艺方案 → 是否有拟采用方案或备选方案？
3. 关键设备参数 → 是否有规格、性能等参数？
4. 投资约束 → 是否有投资控制目标或成本约束？
5. 能耗排放要求 → 是否有具体指标或标准？
6. 建设条件 → 是否有用地、配套、施工等条件？
7. 同类项目资料 → 是否有可参考的案例或参数？

若上述条件大部分缺失，本章仅做**框架性分析**，结论表述为"待补充资料后确定"，并列出资料缺口清单。
"""

REPORT_WORD_LIMITS = {
    "园区发展规划报告": 35000,
    "可行性研究报告": 50000,
    "政府和社会资本合作项目特许经营方案": 30000,
    "产业发展规划报告": 30000,
    "企业发展规划报告": 25000,
    "初步可行性研究报告": 30000,
    "项目申请书(报告)": 30000,
    "项目评估报告": 30000,
    "项目建议书": 30000,
    "资金申请报告": 30000,
    "后评价报告": 30000,
    "社会评价报告": 30000,
    "专题研究报告": 30000,
    "投资机会研究报告": 20000,
}

# ── Per-chapter word limit (fallback only; prefer template JSON values) ──
MAX_WORDS_PER_CHAPTER = {
    "可行性研究报告": 8000,
}
DEFAULT_MAX_WORDS_PER_CHAPTER = 5000

# ── Summary/conclusion chapter word limit (fallback) ──
DEFAULT_SUMMARY_CHAPTER_LIMIT = 3000

# ── Report type -> template file mapping ──
TEMPLATE_MAP = {
    "产业发展规划报告": "chanye_fazhan_guihua.json",
    "企业发展规划报告": "qiye_fazhan_guihua.json",
    "园区发展规划报告": "yuanqu_fazhan_guihua.json",
    "可行性研究报告": "kexingxing_yanjiu.json",
    "政府和社会资本合作项目特许经营方案": "zhengfu_shehuiziben.json",
    "初步可行性研究报告": "chubu_kexingxing.json",
    "项目申请书(报告)": "xiangmu_shenqingshu.json",
    "项目评估报告": "xiangmu_pinggu.json",
    "项目建议书": "xiangmu_jianyishu.json",
    "资金申请报告": "zijin_shenqing.json",
    "后评价报告": "hou_pingjia.json",
    "社会评价报告": "shehui_pingjia.json",
    "专题研究报告": "zhuanti_yanjiu.json",
    "投资机会研究报告": "touzi_jihui.json",
}

# ── Template JSON load cache ──
_template_cache: dict = {}

def _load_template(report_type: str) -> dict | None:
    """Load the template JSON for the given report type, with caching."""
    import json
    if report_type in _template_cache:
        return _template_cache[report_type]
    filename = TEMPLATE_MAP.get(report_type)
    if not filename:
        _template_cache[report_type] = None
        return None
    template_path = PROJECT_ROOT / "generic_knowledge" / "templates" / filename
    if not template_path.exists():
        _template_cache[report_type] = None
        return None
    with open(template_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _template_cache[report_type] = data
    return data

def get_word_limit(report_type: str) -> int:
    """Return the total word limit for the given report type (prefer template JSON value)."""
    tmpl = _load_template(report_type)
    if tmpl and tmpl.get("total_words_max"):
        return tmpl["total_words_max"]
    return 0

def get_chapter_word_limit(report_type: str) -> int:
    """Return the per-chapter word limit for the given report type (prefer template JSON value)."""
    tmpl = _load_template(report_type)
    if tmpl and tmpl.get("per_chapter_max"):
        return tmpl["per_chapter_max"]
    return 0

def get_summary_chapter_limit(report_type: str) -> int:
    """Return the summary/conclusion chapter word limit (prefer template JSON value)."""
    tmpl = _load_template(report_type)
    if tmpl and tmpl.get("summary_chapter_max"):
        return tmpl["summary_chapter_max"]
    return 0

def is_summary_chapter(report_type: str, chapter_seq: int) -> bool:
    """Determine whether the given chapter is a summary/conclusion chapter (read from template JSON)."""
    tmpl = _load_template(report_type)
    if not tmpl or "chapters" not in tmpl:
        return False
    for ch in tmpl["chapters"]:
        if ch.get("seq") == chapter_seq:
            return ch.get("is_summary", False)
    return False

def get_template_notes(report_type: str) -> str:
    """Load the `notes` field of the template for the given report type, used to inject writing conventions."""
    tmpl = _load_template(report_type)
    if not tmpl:
        return ""
    return tmpl.get("notes", "")

def get_template_outline_md(report_type: str) -> str:
    """Return the predefined outline Markdown in the template (the `outline_md` field).

    Returns an empty string if the template has no such field, meaning the outline
    must be generated by the LLM.
    """
    tmpl = _load_template(report_type)
    if not tmpl:
        return ""
    return tmpl.get("outline_md", "")


def get_chapter_template_prompt(report_type: str) -> str:
    """Build a chapter-structure prompt from the template JSON, injected into the system prompt during outline generation."""
    tmpl = _load_template(report_type)
    if not tmpl or "chapters" not in tmpl:
        return ""
    chapters = tmpl["chapters"]
    lines = [f"**{report_type}必须严格遵循以下{len(chapters)}章结构：**\n"]
    for ch in chapters:
        title = ch["title"]
        desc = ch.get("description", "")
        if desc:
            lines.append(f"{title}（{desc}）")
        else:
            lines.append(f"{title}")
    lines.append("\n章标题可微调以适应具体项目，但章数和顺序须与以上模板一致。")
    return "\n".join(lines)

def get_chapter_word_budget(report_type: str, chapter_seq: int) -> int:
    """Return the word budget for the specified chapter (read from the template JSON `word_budget` field)."""
    tmpl = _load_template(report_type)
    if tmpl and "chapters" in tmpl:
        for ch in tmpl["chapters"]:
            if ch.get("seq") == chapter_seq:
                return ch.get("word_budget", 0)
    return 0

# ── Step names ──
STEP_NAMES = [
    "项目信息",
    "导入资料",
    "确定大纲",
    "编写 & 审阅",
    "合并导出",
]

# ── Engineering consulting profession categories (GBZ/T 40846-2021 §3.15, 21 categories) ──
PROFESSIONS = [
    "1. 农业、林业",
    "2. 水利水电",
    "3. 电力（含火电、水电、核电、新能源）",
    "4. 煤炭",
    "5. 石油天然气",
    "6. 公路",
    "7. 铁路、城市轨道交通",
    "8. 民航",
    "9. 水运（含港口河海工程）",
    "10. 电子、信息工程（含通信、广电、信息化）",
    "11. 冶金（含钢铁、有色）",
    "12. 石化、化工、医药",
    "13. 核工业",
    "14. 机械（含智能制造）",
    "15. 轻工、纺织",
    "16. 建材",
    "17. 建筑",
    "18. 市政公用工程",
    "19. 生态建设和环境工程",
    "20. 水文地质、工程测量、岩土工程",
    "21. 其他",
]

# ── Encouraged industries from the Industrial Structure Adjustment Guidance Catalog (2024 edition), 50 categories ──
ENCOURAGED_INDUSTRIES = [
    "一、农林牧渔业",
    "二、水利",
    "三、煤炭",
    "四、电力",
    "五、新能源",
    "六、核能",
    "七、石油天然气",
    "八、钢铁",
    "九、有色金属",
    "十、黄金",
    "十一、石化化工",
    "十二、建材",
    "十三、医药",
    "十四、机械",
    "十五、城市轨道交通装备",
    "十六、汽车",
    "十七、船舶及海洋工程装备",
    "十八、航空航天",
    "十九、轻工",
    "二十、纺织",
    "二十一、建筑",
    "二十二、城镇基础设施",
    "二十三、铁路",
    "二十四、公路及道路运输",
    "二十五、水运",
    "二十六、航空运输",
    "二十七、综合交通运输",
    "二十八、信息产业",
    "二十九、现代物流业",
    "三十、金融服务业",
    "三十一、科技服务业",
    "三十二、商务服务业",
    "三十三、商贸服务业",
    "三十四、旅游业",
    "三十五、邮政业",
    "三十六、教育",
    "三十七、卫生健康",
    "三十八、文化",
    "三十九、体育",
    "四十、养老与托育服务",
    "四十一、家政",
    "四十二、环境保护与资源节约综合利用",
    "四十三、公共安全与应急产品",
    "四十四、民爆和烟花爆竹产品",
    "四十五、人力资源和人力资本服务业",
    "四十六、人工智能",
    "四十七、智能制造",
    "四十八、农业机械装备",
    "四十九、数控机床",
    "五十、网络安全",
]

# ── Feasibility study report chapter template (per 《2023 Edition》 universal/reference outline) ──
_FS_CHAPTER_TEMPLATE = """\n
**可行性研究报告必须严格遵循以下11章结构（政府投资项目），或10章结构（企业投资项目）：**

【政府投资项目 11章】
第一章 概述（项目概况、项目单位概况、编制依据、主要结论和建议）
第二章 项目建设背景和必要性（项目建设背景、规划政策符合性、项目建设必要性）
第三章 项目需求分析与产出方案（需求分析、建设内容和规模、项目产出方案）
第四章 项目选址与要素保障（项目选址或选线、项目建设条件、要素保障分析）
第五章 项目建设方案（技术方案、设备方案、工程方案、用地用海征收补偿安置方案、数字化方案、建设管理方案）
第六章 项目运营方案（运营模式选择、运营组织方案、安全保障方案、绩效管理方案）
第七章 项目投融资与财务方案（投资估算、盈利能力分析、融资方案、债务清偿能力分析、财务可持续性分析）
第八章 项目影响效果分析（经济影响分析、社会影响分析、生态环境影响分析、资源和能源利用效果分析、碳达峰碳中和分析）
第九章 项目风险管控方案（风险识别与评价、风险管控方案、风险应急预案）
第十章 研究结论及建议（主要研究结论、问题与建议）
第十一章 附表、附图和附件

【企业投资项目 10章】
第一章 概述（项目概况、企业概况、编制依据、主要结论和建议）
第二章 项目建设背景、需求分析及产出方案（规划政策符合性、企业发展战略需求分析、项目市场需求分析、项目建设内容和规模及产出方案、项目商业模式）
第三章 项目选址与要素保障（项目选址或选线、项目建设条件、要素保障分析）
第四章 项目建设方案（技术方案、设备方案、工程方案、资源开发方案、用地用海征收补偿安置方案、数字化方案、建设管理方案）
第五章 项目运营方案（生产经营方案、安全保障方案、运营管理方案）
第六章 项目投融资与财务方案（投资估算、盈利能力分析、融资方案、债务清偿能力分析、财务可持续性分析）
第七章 项目影响效果分析（经济影响分析、社会影响分析、生态环境影响分析、资源和能源利用效果分析、碳达峰碳中和分析）
第八章 项目风险管控方案（风险识别与评价、风险管控方案、风险应急预案）
第九章 研究结论及建议（主要研究结论、问题与建议）
第十章 附表、附图和附件

默认按政府投资项目11章结构生成。若项目主题明确为企业自筹资金/商业投资/市场化经营行为，则按企业投资项目10章结构生成。章节标题和顺序不可增删或打乱。
"""

# ── Load .env (priority: env var > user data dir .env > resource dir .env) ──
_env_loaded = False

def _find_dotenv() -> Path | None:
    """Find the .env file by priority: writable data directory first, then resource directory."""
    candidates = []
    if DATA_ROOT != RESOURCE_DIR:
        candidates.append(DATA_ROOT / ".env")
    candidates.append(RESOURCE_DIR / ".env")
    for p in candidates:
        if p.exists():
            return p
    return None

_env_path = _find_dotenv()
if _env_path and not _env_loaded:
    from dotenv import load_dotenv
    load_dotenv(_env_path)
    _env_loaded = True

# ── Override static constants via .env (runtime dynamic configuration) ──
def _env_str(key: str, default: str) -> str:
    """Read an environment variable; empty string is treated as unset."""
    val = os.getenv(key)
    if val is not None and val != "":
        return val
    return default

def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ[key])
    except (KeyError, ValueError):
        return default

def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ[key])
    except (KeyError, ValueError):
        return default

def _env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None or val == "":
        return default
    return val.lower() in ("true", "1", "yes")

DEFAULT_MODEL = _env_str("DEFAULT_MODEL", DEFAULT_MODEL)
DEFAULT_BASE_URL = _env_str("DEFAULT_BASE_URL", DEFAULT_BASE_URL)
EMBED_MODEL_NAME = _env_str("EMBED_MODEL_NAME", EMBED_MODEL_NAME)
CHUNK_SIZE = _env_int("CHUNK_SIZE", CHUNK_SIZE)
CHUNK_OVERLAP = _env_int("CHUNK_OVERLAP", CHUNK_OVERLAP)

# FRL-003: ensure overlap < size to prevent infinite loop in _chunk_segment
if CHUNK_OVERLAP >= CHUNK_SIZE:
    import warnings
    warnings.warn(f"CHUNK_OVERLAP ({CHUNK_OVERLAP}) >= CHUNK_SIZE ({CHUNK_SIZE}), clamping overlap to size//4")
    CHUNK_OVERLAP = max(0, CHUNK_SIZE // 4)
RAG_RESULTS_PER_SOURCE = _env_int("RAG_RESULTS_PER_SOURCE", RAG_RESULTS_PER_SOURCE)
RERANK_ENABLED = _env_bool("RERANK_ENABLED", RERANK_ENABLED)
TEMPERATURE_OUTLINE = _env_float("TEMPERATURE_OUTLINE", TEMPERATURE_OUTLINE)
TEMPERATURE_WRITING = _env_float("TEMPERATURE_WRITING", TEMPERATURE_WRITING)
