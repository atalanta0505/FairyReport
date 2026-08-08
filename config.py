"""FairyReport global configuration.

The public edition contains workflow defaults only. Report methods, reference
materials, and organization-specific guidance are supplied by users at runtime.
"""

import os
from pathlib import Path
import sys as _sys


def _get_base_dir() -> Path:
    """Return the writable data root directory."""
    env_data = os.environ.get("FRL_DATA_DIR")
    if env_data:
        return Path(env_data)
    if getattr(_sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "FairyReport"
        return Path.cwd() / "FairyReportData"
    return Path(__file__).parent


def _get_resource_dir() -> Path:
    """Return the read-only application resource directory."""
    if getattr(_sys, "frozen", False):
        return Path(_sys._MEIPASS)
    return Path(__file__).parent


PROJECT_ROOT = _get_resource_dir()
RESOURCE_DIR = PROJECT_ROOT
DATA_ROOT = _get_base_dir()

# User-managed data. None of these directories belong in the public repository.
GENERIC_KB_DIR = DATA_ROOT / "data/knowledge"
GENERIC_DB_DIR = DATA_ROOT / "data/vector_db/shared"
PROJECTS_DIR = DATA_ROOT / "data/projects"

# LLM configuration
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
SOURCE_URL = ""

# Embedding and retrieval
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
RAG_RESULTS_PER_SOURCE = 5
RERANK_ENABLED = False
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
RERANK_BASE_URL = "https://api.siliconflow.cn/v1/rerank"

# Generation parameters
TEMPERATURE_OUTLINE = 0.2
TEMPERATURE_ORDER = 0.1
TEMPERATURE_HINT = 0.3
TEMPERATURE_WRITING = 0.2
TEMPERATURE_MODIFY = 0.2
FREQUENCY_PENALTY = 0.4
PRESENCE_PENALTY = 0.25
TOP_P = 0.85

# These are interface conveniences, not fixed report templates. Users may enter
# any report type or consulting domain in the project form.
REPORT_TYPES = [
    "通用咨询报告",
    "研究分析报告",
    "战略规划报告",
    "评估报告",
    "实施方案",
    "自定义",
]

CONSULTING_DOMAINS = [
    "综合",
    "战略与组织",
    "市场与行业",
    "运营与流程",
    "数字化与技术",
    "公共事务与社会研究",
    "其他",
]

# Public, domain-neutral review method. It describes evidence and reasoning
# quality rather than prescribing the content or structure of any report type.
QUALITY_REVIEW_SYSTEM_PROMPT = """\
你是咨询报告质量审校员。请检查给定章节的方法质量和表达质量。

检查维度：
1. 目标一致性：章节是否回应报告目标和当前标题。
2. 证据边界：事实、用户资料、推断和待核实事项是否清楚区分。
3. 论证链条：结论是否有证据和推理支撑，是否存在逻辑跳跃。
4. 方案比较：需要决策时，是否说明备选方案、比较维度和取舍理由。
5. 可执行性：建议是否包含对象、动作、条件、优先级或后续步骤。
6. 风险与限制：是否说明不确定性、适用边界和关键风险。
7. 表达质量：是否存在重复、空泛表述或无依据的确定性判断。

请严格按以下格式输出：
【校核结果】通过 / 需补充 / 不适用
【原因说明】简要说明判定理由
【校核详情】逐项列出发现
【修改建议】给出具体可执行的修改建议
【需补充资料清单】仅在“需补充”时列出
"""

UNIVERSAL_ANALYSIS_FRAMEWORK = """\
## 通用分析方法

围绕当前章节选择必要的方法，不机械套用固定结构：
1. 界定问题、目标、范围和关键约束。
2. 基于用户资料和可追溯来源陈述事实，区分事实与判断。
3. 解释关键发现之间的因果、条件或权衡关系。
4. 涉及选择时，给出可比较的选项、评价维度和推荐理由。
5. 将建议写成可执行动作，并说明责任对象、前置条件或验证方式。
6. 说明风险、不确定性、适用边界和仍需补充的信息。
"""

EVIDENCE_BOUNDARY_RULES = """\
## 证据边界

- 不得编造用户未提供的机构、数字、日期、案例或来源。
- 缺少关键信息时使用“待补充”或条件性表述，并列出资料缺口。
- 事实性陈述应引用现有资料；一般性分析必须明确其为分析判断。
- 推荐结论必须能追溯到目标、证据、比较过程或明确假设。
"""

REPORT_WORD_LIMITS = {
    "通用咨询报告": 30000,
    "研究分析报告": 30000,
    "战略规划报告": 30000,
    "评估报告": 25000,
    "实施方案": 20000,
    "自定义": 30000,
}
DEFAULT_REPORT_WORD_LIMIT = 30000
DEFAULT_MAX_WORDS_PER_CHAPTER = 5000
DEFAULT_SUMMARY_CHAPTER_LIMIT = 3000


def get_word_limit(report_type: str) -> int:
    return REPORT_WORD_LIMITS.get(report_type, DEFAULT_REPORT_WORD_LIMIT)


def get_chapter_word_limit(report_type: str) -> int:
    return DEFAULT_MAX_WORDS_PER_CHAPTER


def get_summary_chapter_limit(report_type: str) -> int:
    return DEFAULT_SUMMARY_CHAPTER_LIMIT


def is_summary_chapter(report_type: str, chapter_seq: int) -> bool:
    """No report-specific chapter semantics are embedded in the public edition."""
    return False


def get_chapter_word_budget(report_type: str, chapter_seq: int) -> int:
    return get_chapter_word_limit(report_type)


STEP_NAMES = [
    "项目信息",
    "导入资料",
    "确定大纲",
    "编写 & 审阅",
    "合并导出",
]


_env_loaded = False


def _find_dotenv() -> Path | None:
    candidates = []
    if DATA_ROOT != RESOURCE_DIR:
        candidates.append(DATA_ROOT / ".env")
    candidates.append(RESOURCE_DIR / ".env")
    for path in candidates:
        if path.exists():
            return path
    return None


_env_path = _find_dotenv()
if _env_path and not _env_loaded:
    from dotenv import load_dotenv

    load_dotenv(_env_path)
    _env_loaded = True


def _env_str(key: str, default: str) -> str:
    value = os.getenv(key)
    return value if value else default


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
    value = os.getenv(key)
    if not value:
        return default
    return value.lower() in ("true", "1", "yes")


DEFAULT_MODEL = _env_str("DEFAULT_MODEL", DEFAULT_MODEL)
DEFAULT_BASE_URL = _env_str("DEFAULT_BASE_URL", DEFAULT_BASE_URL)
SOURCE_URL = _env_str("FRL_SOURCE_URL", SOURCE_URL)
EMBED_MODEL_NAME = _env_str("EMBED_MODEL_NAME", EMBED_MODEL_NAME)
CHUNK_SIZE = _env_int("CHUNK_SIZE", CHUNK_SIZE)
CHUNK_OVERLAP = _env_int("CHUNK_OVERLAP", CHUNK_OVERLAP)

if CHUNK_OVERLAP >= CHUNK_SIZE:
    import warnings

    warnings.warn(
        f"CHUNK_OVERLAP ({CHUNK_OVERLAP}) >= CHUNK_SIZE ({CHUNK_SIZE}); "
        "clamping overlap to size//4"
    )
    CHUNK_OVERLAP = max(0, CHUNK_SIZE // 4)

RAG_RESULTS_PER_SOURCE = _env_int("RAG_RESULTS_PER_SOURCE", RAG_RESULTS_PER_SOURCE)
RERANK_ENABLED = _env_bool("RERANK_ENABLED", RERANK_ENABLED)
TEMPERATURE_OUTLINE = _env_float("TEMPERATURE_OUTLINE", TEMPERATURE_OUTLINE)
TEMPERATURE_WRITING = _env_float("TEMPERATURE_WRITING", TEMPERATURE_WRITING)
