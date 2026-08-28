"""
章节写作 — 移植自根目录 writer.py（v1.0.5）。

- 技术分析三件、字数预算分配、parse_tech_review_result 等价移植
- 模板函数改调 templates_loader；提示词/配置常量改自 prompts
- ChapterWriter 用 engine LLMClient（httpx 直连，用户 Key 随请求传入）
"""
import json
import re

from . import templates_loader as tmpl
from .prompts import (
    COMPLIANCE_REVIEW_SYSTEM_PROMPT,
    FAST_REVIEW_SYSTEM_PROMPT,
    FREQUENCY_PENALTY,
    FULL_EXPERT_REVIEW_SYSTEM_PROMPT,
    NUMERICAL_REVIEW_SYSTEM_PROMPT,
    PRESENCE_PENALTY,
    REASONING_CHINESE_DEFENSE_PROMPT,
    TECH_ANALYSIS_ALWAYS_REPORT_TYPES,
    TECH_ANALYSIS_CONDITIONAL_REPORT_TYPES,
    TECH_CHAPTER_KEYWORDS,
    TECH_INSUFFICIENT_DATA_RULES,
    TECH_REVIEW_SYSTEM_PROMPT,
    TECH_WRITING_FRAMEWORK,
    TEMPERATURE_HINT,
    TEMPERATURE_MODIFY,
    TEMPERATURE_WRITING,
    TOP_P,
    _BASE_WRITING_PROMPT,
    _HINT_SYSTEM_PROMPT,
    _MODIFY_SYSTEM_PROMPT,
)

# ═══════════════════════════════════════════════════════════════
# 技术分析规则构建（v1.0.4）
# ═══════════════════════════════════════════════════════════════


def _chapter_has_tech_keyword(chapter_title: str) -> bool:
    """章标题是否含技术相关关键词。"""
    if not chapter_title:
        return False
    return any(kw in chapter_title for kw in TECH_CHAPTER_KEYWORDS)


def _is_tech_analysis_applicable(report_type: str, chapter_title: str,
                                  topic: str = "") -> bool:
    """是否对该章启用技术分析增强规则。"""
    if not _chapter_has_tech_keyword(chapter_title):
        return False

    if report_type in TECH_ANALYSIS_ALWAYS_REPORT_TYPES:
        return True

    if report_type in TECH_ANALYSIS_CONDITIONAL_REPORT_TYPES:
        return bool(topic) and any(kw in topic for kw in [
            "工艺", "技术", "设备", "工程", "产线", "制造",
            "生产", "数字化", "智能化", "能源", "环保",
        ])

    return True


def _build_tech_analysis_rules(report_type: str, chapter_title: str,
                                topic: str = "") -> str:
    """构建注入写作 system prompt 的技术分析规则块；不适用返回空串。"""
    if not _is_tech_analysis_applicable(report_type, chapter_title, topic):
        return ""
    return TECH_WRITING_FRAMEWORK + "\n\n" + TECH_INSUFFICIENT_DATA_RULES


# ── 章节写作 system prompt ──
def _build_writing_system_prompt(report_type: str = "",
                                  total_words: int = 0,
                                  total_chapters: int = 0,
                                  writing_hint: str = "",
                                  chapter_budget: int = 0,
                                  is_summary: bool = False,
                                  chapter_title: str = "",
                                  topic: str = "") -> str:
    base = _BASE_WRITING_PROMPT
    if report_type:
        base += f"\n\n当前报告类型：**{report_type}**，请使用该类型报告的专业表述方式。"

    rules = """
核心规则：
0. **禁止开场白**：不要输出任何"好的"、"作为专家"、"我将"等确认语或自我介绍，直接从章节标题和正文开始。
1. **大纲锁定**：严格按大纲中的标题文字和层级写作，绝不修改任何标题
2. **引用格式**：引用时只能使用上方「参考资料」中实际出现的来源标签。项目资料使用【源:文件名】，国家与行业规程标准使用【标:规程标准全称】，百度联网检索结果使用【网:标题】。**严禁编造不存在的来源标签，严禁输出孤立的 [Z] 标记**——若无对应来源直接撰写专业正文论述即可，无需添加任何虚构标签。导出时系统将统一生成参考文献编号。
3. **逻辑连贯**：如果前文已有相关数据或结论，请在基础上自然衔接
4. **专业表达**：使用工程咨询行业的标准术语和表述方式
5. **内容充实**：每节/小节都要有实质性内容，不要空洞
8. **Markdown 格式规范与发改委 12 项规定动作标准三线表（极重要）**：每个标题（#、##、###、####）必须独占一行且强制空一行（输出 \\n\\n）后再写正文，严禁标题与正文连在同一行，严禁同名同句同排！在涉及主要技术经济指标表（1.1.6）、建设规模比选（3.2.1）、场址比选（4.1.2）、技术路线比选（5.1.1）、关键设备比选（5.2.1）、主要设备清单（5.2.2）、工程方案比选（5.3.1）、项目总投资与建设投资估算表/分年度资金计划（7.1.2/7.1.5，按发改委教材全要素包含建筑工程费、设备购置费、安装工程费、工程建设其他费、基本预备费、涨价预备费、建设期利息、流动资金等）、主要财务指标汇总（7.2.3，包含全要素 FIRR、FNPV、Pt、ROI、ROE）、融资方案比选（7.3.1）、债务清偿能力指标（7.4.3，包含 ICR、DSCR、资产负债率）、风险评价矩阵（9.1.8）等小节，必须强制输出标准 Markdown 三线表格（含表头、对齐线、量纲单位及推荐结论），表格每行末尾必须输出标准换行符 \\n，表格前后强制空一行，严禁使用 || 连写在同一行！"""

    if total_words > 0 and total_chapters > 0:
        rules += f"\n6. **篇幅建议**：全篇目标{total_words:,}字，共{total_chapters}章。每章有建议字数（见规则7），请尽量控制在预算范围内。"

    if chapter_budget > 0:
        lo = int(chapter_budget * 0.9)
        hi = int(chapter_budget * 1.1)
        if is_summary:
            rules += f"\n7. **本章字数**：本章为综述/总结性章节，预算 **{chapter_budget:,} 字**。请精炼概括，控制在 {lo:,}–{hi:,} 字范围内。"
        else:
            rules += f"\n7. **本章字数建议**：本章建议 **{chapter_budget:,} 字**（仅计正文，标题不占字数）。每个小节有参考配额（见 user prompt 底部结构框架），请按配额逐节分配内容密度。"

    template_notes = tmpl.get_template_notes(report_type)
    rule_num = 8 if chapter_budget > 0 else 7
    if template_notes:
        rules += f"\n{rule_num}. **模板规范**：{template_notes}"

    tech_rules = _build_tech_analysis_rules(report_type, chapter_title or "", topic or "")
    if tech_rules:
        rules += "\n\n" + tech_rules

    if writing_hint:
        rules += f"\n\n本章编写提示：{writing_hint}"

    return base + "\n" + rules


def _count_chapters(outline_md: str) -> int:
    """统计大纲中章标题数。"""
    matches = re.findall(r'^#\s+第.+章', outline_md, re.MULTILINE)
    return len(matches) or 1


def _trim_outline_to_position(outline_md: str, allowed_seqs: list) -> str:
    """裁剪大纲，只保留 allowed_seqs 中的章（写作顺序位置 <= 当前章）。"""
    lines = outline_md.split('\n')
    result = []
    in_chapter = True
    current_seq = 0
    ch_pattern = re.compile(r'^#\s+(?:第\s*([一二三四五六七八九十百零\d]+)\s*章|(\d+)[\.\s])')

    chinese_to_int = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
    }
    allowed_set = set(allowed_seqs)

    for line in lines:
        m = ch_pattern.match(line)
        if m:
            cn_num = m.group(1)
            ar_num = m.group(2)
            if cn_num:
                if cn_num.isdigit():
                    current_seq = int(cn_num)
                else:
                    current_seq = chinese_to_int.get(cn_num, 0)
            elif ar_num:
                current_seq = int(ar_num)
            in_chapter = (current_seq in allowed_set)

        if in_chapter:
            result.append(line)

    return '\n'.join(result)


def _count_chinese_chars(text: str) -> int:
    """统计有效字符（中文 + 全角标点 + CJK 空格）。"""
    return len(re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', text))


def _strip_markdown_headings(text: str) -> str:
    """去除 Markdown 标题行，保留正文。"""
    return re.sub(r'^#{1,6}\s+.*$', '', text, flags=re.MULTILINE)


def _strip_markdown_tables(text: str) -> str:
    """去除 Markdown 表格行，保留纯正文。"""
    return re.sub(r'^\s*\|.*?\|\s*$', '', text, flags=re.MULTILINE)


def _count_content_chars(text: str) -> int:
    """统计纯正文有效中文字符计数（不含标题与表格）。"""
    no_headings = _strip_markdown_headings(text)
    no_tables = _strip_markdown_tables(no_headings)
    return _count_chinese_chars(no_tables)


# ── 大纲层级解析与每节字数预算分配 ──

def _extract_chapter_skeleton(outline_md: str, chapter_seq: int) -> str:
    """从大纲 Markdown 中提取指定章的纯结构骨架标题行（#、##、###、####、##### 等）。"""
    if not outline_md or chapter_seq <= 0:
        return ""

    lines = outline_md.split('\n')
    _cn_nums = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
                '二十一', '二十二', '二十三', '二十四', '二十五', '二十六', '二十七', '二十八', '二十九', '三十']
    cn_num = _cn_nums[chapter_seq] if chapter_seq < len(_cn_nums) else str(chapter_seq)

    ch_pattern = re.compile(
        r'^#\s+(?:第\s*(?:' + str(chapter_seq) + r'|' + cn_num + r')\s*章|' + str(chapter_seq) + r'[\.\s])'
    )
    in_chapter = False
    skeleton_lines = []

    for line in lines:
        stripped = line.strip()
        if ch_pattern.match(stripped):
            in_chapter = True
            skeleton_lines.append(stripped)
            continue

        if in_chapter:
            if re.match(r'^#\s+', stripped) and not stripped.startswith('##'):
                break
            if stripped.startswith('#'):
                skeleton_lines.append(stripped)

    return '\n'.join(skeleton_lines)


def _parse_outline_hierarchy(outline_md: str, chapter_seq: int) -> dict:
    """解析给定章的 H2/H3 层级。"""
    lines = outline_md.split('\n')
    result = {"chapter_title": "", "h2_sections": []}

    _cn_nums = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
                '二十一', '二十二', '二十三', '二十四', '二十五', '二十六', '二十七', '二十八', '二十九', '三十']
    cn_num = _cn_nums[chapter_seq] if chapter_seq < len(_cn_nums) else str(chapter_seq)

    ch_pattern = re.compile(
        r'^#\s+(?:第\s*(?:' + str(chapter_seq) + r'|' + cn_num + r')\s*章|' + str(chapter_seq) + r'[\.\s])'
    )
    in_chapter = False
    current_h2 = None

    for line in lines:
        if ch_pattern.match(line):
            in_chapter = True
            result["chapter_title"] = re.sub(r'^#\s+', '', line).strip()
            continue
        if in_chapter and re.match(r'^#\s+', line) and not line.startswith('##'):
            break

        if not in_chapter:
            continue

        if re.match(r'^##\s+', line):
            title = re.sub(r'^##\s+', '', line).strip()
            current_h2 = {"title": title, "level": 2, "h3_subsections": []}
            result["h2_sections"].append(current_h2)
        elif re.match(r'^###\s+', line) and current_h2 is not None:
            title = re.sub(r'^###\s+', '', line).strip()
            current_h2["h3_subsections"].append({"title": title, "level": 3})

    return result


def _allocate_section_budgets(hierarchy: dict, chapter_budget: int) -> dict:
    """将字数预算分配到各 H3 子节。

    策略：按 H2 均分，H2 内按 H3 均分，结果取整到 50。
    """
    h2_sections = hierarchy["h2_sections"]
    if not h2_sections:
        return {"h2_sections": [], "total_allocated": 0}

    total_h3 = sum(len(h2["h3_subsections"]) for h2 in h2_sections)
    if total_h3 == 0:
        per_h2 = max(50, chapter_budget // len(h2_sections))
        for h2 in h2_sections:
            h2["budget"] = per_h2
        return {"h2_sections": h2_sections, "total_allocated": per_h2 * len(h2_sections)}

    per_h3_raw = chapter_budget / total_h3
    per_h3 = max(50, (per_h3_raw // 50) * 50)

    total = 0
    for h2 in h2_sections:
        h3_count = len(h2["h3_subsections"])
        h2_budget = int(per_h3 * h3_count)
        h2["budget"] = h2_budget
        for h3 in h2["h3_subsections"]:
            h3["budget"] = int(per_h3)
        total += h2_budget

    remainder = chapter_budget - total
    if remainder > 0 and h2_sections:
        h2_sections[0]["budget"] += remainder
        if h2_sections[0]["h3_subsections"]:
            h2_sections[0]["h3_subsections"][0]["budget"] += remainder

    return {"h2_sections": h2_sections, "total_allocated": chapter_budget}


def _build_section_quota_block(hierarchy: dict, allocation: dict) -> str:
    """生成"结构参考与小节篇幅建议"提示块（彻底废除句数硬控制与压缩限制，鼓励深度充实展开）。"""
    h2_sections = allocation.get("h2_sections", [])
    if not h2_sections:
        return ""

    chapter_title = hierarchy.get("chapter_title", "")

    lines = [
        f"\n## 📐 结构参考与小节篇幅建议",
        f"「{chapter_title}」建议 **{allocation['total_allocated']:,} 字**（仅计正文，标题不计入）。",
        f"以下为各小节的参考字数配置，请展开详实论述：\n",
    ]

    for i, h2 in enumerate(h2_sections):
        h3s = h2["h3_subsections"]
        h3_list = "、".join(h3["title"] for h3 in h3s) if h3s else "（无小节）"
        if h3s:
            lines.append(f"- **{h2['title']}**（参考篇幅约 {h2['budget']:,} 字，含 {len(h3s)} 小节：{h3_list}）")
            for h3 in h3s:
                b = h3.get("budget", 0)
                lines.append(
                    f"  - {h3['title']}（建议深度论证，参考篇幅约 {b:,} 字）"
                )
        else:
            b = h2.get("budget", 0)
            lines.append(
                f"- **{h2['title']}**（建议深度论证，参考篇幅约 {b:,} 字）"
            )

    lines.append(
        f"\n**总字数建议约 {allocation['total_allocated']:,} 字（仅作为宏观参考）。请展开详实充实的专业工程论证、参数核算与合规分析，杜绝空洞简略与内容缩水！**"
    )

    return "\n".join(lines)


def check_chapter_word_limit(content: str, report_type: str, chapter_title: str, ch_seq: int):
    """后置校验：章字数是否在预算内。返回 (is_over, wc, budget, warning_msg)。"""
    budget = tmpl.get_chapter_word_budget(report_type, ch_seq)
    wc = _count_chinese_chars(content)
    ratio = (wc / budget * 100) if budget > 0 else 0

    if budget > 0 and wc > budget * 1.15:
        over = int(ratio - 100)
        msg = (f"实际字数{wc:,}字，计划字数{budget:,}字，"
               f"实际字数超过计划字数{over}%")
        return True, wc, budget, msg
    elif budget > 0 and wc < budget * 0.85:
        pct = int(ratio)
        msg = (f"实际字数{wc:,}字，计划字数{budget:,}字，"
               f"实际字数为计划字数的{pct}%，建议充实")
        return True, wc, budget, msg
    elif budget > 0:
        pct = int(ratio)
        msg = (f"实际字数{wc:,}字，计划字数{budget:,}字，"
               f"实际字数为计划字数的{pct}%，达标 ✓")
        return False, wc, budget, msg
    return False, wc, budget, ""


def normalize_chapter_markdown(text: str, skeleton: str = "") -> str:
    """章节 Markdown 规范化清洗：
    1. 还原 CRLF 为 LF
    2. 在所有非换行符/非#紧邻的 #{1,6} 前强制补双换行符
    3. 表格单行 || 还原为多行
    4. 标题与加粗/引用/表格粘连拆解
    5. 若传入骨架，提取骨架中的各级标题，无条件在已知标题边界处截断并插入双换行
    6. 通用单行标题紧连中文/标点断行保护
    7. 确保每个标题行下方强制空一行（若紧跟非空正文行且未空行，补空行）
    """
    if not text or not isinstance(text, str):
        return ""
    cleaned = text.replace("\r\n", "\n")

    # 1. 在所有非换行符/非#紧邻的 #{1,6} 前强制补双换行符
    cleaned = re.sub(r'([^#\n])\s*(#{1,6}\s+)', r'\1\n\n\2', cleaned)

    # 2. 表格单行 || 还原
    cleaned = re.sub(r'\|\s*\|', '|\n|', cleaned)
    cleaned = re.sub(r'^([^|\n].*?)(\|.+?\|\s*\n\s*\|[-: ]+?\|)', r'\1\n\n\2', cleaned, flags=re.MULTILINE)

    # 3. 标题与加粗/引用/表格粘连拆解
    cleaned = re.sub(r'(#{1,6}\s+[^\n*|【]*?)\s*(\*\*|【源|\|)', r'\1\n\n\2', cleaned)

    # 4. 骨架已知标题匹配断行
    if skeleton:
        known_headings = []
        for line in skeleton.split("\n"):
            line = line.strip()
            m = re.match(r'^#{1,6}\s+(.+)$', line)
            if m:
                h = m.group(1).strip()
                if h:
                    known_headings.append(h)
                    no_prefix = re.sub(r'^(?:第[一二三四五六七八九十百零\d]+章|\d+(?:\.\d+)*)\s*', '', h).strip()
                    if no_prefix:
                        known_headings.append(no_prefix)
        known_headings.sort(key=len, reverse=True)
        for h in known_headings:
            escaped = re.escape(h)
            pattern = rf'^(#{{1,6}}\s+(?:\d+(?:\.\d+)*\s+)?{escaped})\s*([:：，。—\-\u2014\u2013\s]*)([^\n]+)$'
            def _repl(m):
                h_part = m.group(1)
                rest = m.group(3)
                clean_rest = re.sub(r'^[:：—\-\u2014\u2013,，。\s]+', '', rest).strip()
                return f"{h_part}\n\n{clean_rest}" if clean_rest else h_part
            cleaned = re.sub(pattern, _repl, cleaned, flags=re.MULTILINE)

    # 5. 单行标题后紧跟冒号/句号/破折号等拆分
    pattern_punct = r'^(#{1,6}\s+[^\n:：。—\-\u2014\u2013]{2,50}?)\s*([:：。—\-\u2014\u2013]+)\s*([^\n]+)$'
    def _repl_punct(m):
        title_part = m.group(1)
        rest = m.group(3)
        clean_rest = re.sub(r'^[:：。—\-\u2014\u2013\s]+', '', rest).strip()
        return f"{title_part}\n\n{clean_rest}" if clean_rest else title_part
    cleaned = re.sub(pattern_punct, _repl_punct, cleaned, flags=re.MULTILINE)

    # 6. 确保标题与正文之间有空行（如 ### 1.1 标题\n正文 -> ### 1.1 标题\n\n正文）
    cleaned = re.sub(r'^(#{1,6}\s+[^\n]+)\n(?!\n|#{1,6}\s)', r'\1\n\n', cleaned, flags=re.MULTILINE)

    return cleaned


class ChapterWriter:
    def __init__(self, llm, report_type: str = "", total_words: int = 0):
        self.llm = llm
        self.report_type = report_type
        self.total_words = total_words

    # ── 写作提示生成 ──
    def generate_hint(self, chapter_title: str, chapter_seq: int,
                      outline_md: str, writing_order: list,
                      predecessor_hints: dict = None,
                      report_name: str = "",
                      user_instruction: str = "",
                      existing_hint: str = "") -> str:
        """为给定章生成写作提示。"""
        pos = writing_order.index(chapter_seq)
        trimmed_outline = _trim_outline_to_position(outline_md, writing_order[:pos + 1])

        wo_str = " → ".join(str(s) for s in writing_order)
        is_first = (pos == 0)
        predecessor_seqs = writing_order[:pos]

        prompt = (
            f"报告类型：{self.report_type}\n"
            f"项目名称：{report_name}\n"
            f"大纲（仅含已编写或待编写的章节，后续章已隐藏）：\n{trimmed_outline}\n\n"
            f"编写顺序：{wo_str}\n"
            f"当前章「{chapter_title}」处于第 {pos + 1} 顺位\n"
        )
        if is_first:
            prompt += "（当前章是写作顺序第 1 顺位，无前序章）\n\n"
        else:
            prompt += f"前序章：第 {'、'.join(str(s) for s in predecessor_seqs)} 章\n\n"
            if predecessor_hints:
                prompt += "已生成的前序章提示词：\n"
                for seq in predecessor_seqs:
                    hint = predecessor_hints.get(seq, "")
                    if hint:
                        prompt += f"- 第{seq}章提示词：{hint}\n"
                prompt += "\n"

        if user_instruction:
            prompt += (
                f"⚠️ 修改模式：请根据用户意图调整现有提示词。\n"
                f"用户修改意图：{user_instruction}\n"
                f"现有提示词：{existing_hint or '（无）'}\n"
            )
            prompt += "\n"

        prompt += f"请为「{chapter_title}」撰写编写提示：\n\n{REASONING_CHINESE_DEFENSE_PROMPT}"
        hint = self.llm.chat(prompt, system_prompt=_HINT_SYSTEM_PROMPT,
                             temperature=TEMPERATURE_HINT).strip()
        return hint

    # ── 章节写作（非流式）──
    def write_chapter(self, chapter_title: str, outline_md: str,
                      predecessor_chapters: dict, rag_context: str,
                      topic: str, writing_hint: str = "",
                      report_name: str = "",
                      chapter_budget: int = 0,
                      is_summary: bool = False) -> str:
        prompt, system = self._build_chapter_write_args(
            chapter_title, outline_md, predecessor_chapters, rag_context, topic, writing_hint,
            report_name=report_name, chapter_budget=chapter_budget, is_summary=is_summary,
        )
        ch_seq = self._parse_chapter_seq(chapter_title)
        skeleton = _extract_chapter_skeleton(outline_md, ch_seq) if ch_seq > 0 else ""
        raw_res = self.llm.chat(prompt, system_prompt=system, temperature=TEMPERATURE_WRITING,
                                frequency_penalty=FREQUENCY_PENALTY,
                                presence_penalty=PRESENCE_PENALTY,
                                top_p=TOP_P)
        return normalize_chapter_markdown(raw_res, skeleton=skeleton)

    # ── 章节写作（流式）──
    def write_chapter_stream(self, chapter_title: str, outline_md: str,
                              predecessor_chapters: dict, rag_context: str,
                              topic: str, callback=None, writing_hint: str = "",
                              report_name: str = "",
                              chapter_budget: int = 0,
                              is_summary: bool = False) -> str:
        prompt, system = self._build_chapter_write_args(
            chapter_title, outline_md, predecessor_chapters, rag_context, topic, writing_hint,
            report_name=report_name, chapter_budget=chapter_budget, is_summary=is_summary,
        )
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        return self.llm.chat_stream(messages, temperature=TEMPERATURE_WRITING,
                                    callback=callback,
                                    frequency_penalty=FREQUENCY_PENALTY,
                                    presence_penalty=PRESENCE_PENALTY,
                                    top_p=TOP_P)

    # ── 章节写作参数构建（含字数预算注入）──
    def _build_chapter_write_args(self, chapter_title: str, outline_md: str,
                                   predecessor_chapters: dict, rag_context: str,
                                   topic: str, writing_hint: str = "",
                                   report_name: str = "",
                                   chapter_budget: int = 0,
                                   is_summary: bool = False) -> tuple:
        """返回 (prompt, system)。含 RAG、字数预算、适用时技术分析框架。"""
        prev_context = self._build_prev_context(predecessor_chapters)
        ch_seq = self._parse_chapter_seq(chapter_title)
        skeleton = _extract_chapter_skeleton(outline_md, ch_seq) if ch_seq > 0 else ""

        report_label = f"## 项目名称\n{report_name}\n\n## 产业方向\n{topic}" if report_name else f"## 项目主题\n{topic}"

        prompt = (
            f"{report_label}\n\n"
            f"## 完整大纲 [{self.report_type}]\n{outline_md}\n\n"
            f"## 当前章节\n请编写「{chapter_title}」的正文内容\n\n"
        )

        if skeleton:
            prompt += f"## 待填充的本章结构骨架（已锁定）\n{skeleton}\n\n"

        if prev_context:
            prompt += f"## 前文已完成章节（供参考衔接）\n{prev_context}\n\n"

        if rag_context and "无相关参考资料" not in rag_context:
            prompt += f"## 参考资料（RAG 检索结果）\n{rag_context}\n\n"

        prompt += (
            f"## 写作要求（骨架靶向填充模式）\n"
            f"- **骨架锁定（最高优先级）：必须严格保留上方【待填充的本章结构骨架】中的所有标题行（#、##、###、####）及其完整文字与层级，严禁增删、修改或调换任何标题顺序！**\n"
            f"- **发改委 12 项规定动作标准三线表格强制规范（最高优先级）：在涉及主要技术经济指标（1.1.6）、建设规模方案比选（3.2.1）、场址方案比选（4.1.2）、技术路线比选（5.1.1）、关键设备比选（5.2.1）、主要设备清单（5.2.2）、工程方案比选（5.3.1）、投资估算构成与资金计划（7.1.2/7.1.5）、财务评价指标（7.2.3）、融资方案比选（7.3.1）、债务清偿能力（7.4.3）、风险评价管控矩阵（9.1.8）等小节，必须强制输出标准的 Markdown 三线表格（表头 + 对齐分隔线如 `| :--- | :---: | ---: |` + 完整数据行、工程量纲单位及推荐结论），严禁全篇纯文字堆砌！**\n"
            f"- **末级小节精准填充：在每一个最低级别标题（### / ####）下方强制空一行（\\n\\n），直接开始深入填充详实、专业、严谨的正文分析、工程参数、合规论证与数据表格！**\n"
            f"- **非末级标题禁止堆砌正文：一级章（#）和二级节（##）作为分类与结构导引，正文必须具体归属到对应的末级小节下方！**\n"
            f"- **内容深度与充实展开（极重要）：全面展开实质性工程分析、技术论证、详实参数核算、政策背景契合度推演与合规论证，每小节论述充分详尽，杜绝空洞简略与短句敷衍！**\n"
            f"- **格式规范（极重要）：每个标题（#、##、###、####）必须独占一行且强制空一行（\\n\\n）后再写正文，严禁标题与正文连在同一行，严禁标题与正文首句同名同句同排连写（例如严禁输出'### 1.1.1 建设地点：本项目位于...'，正确格式为'### 1.1.1 建设地点\\n\\n本项目位于...'）；表格每行末尾必须输出标准换行符 \\n，表格前后强制空一行，严禁使用 || 连写在同一行！**\n"
            f"- 对事实性陈述插入引用标记：只能使用上方「参考资料」中实际出现的标签【源:文件名】、【标:规程标准】或【网:标题】，严禁输出孤立的 [Z] 标记\n"
            f"- 请输出完整的章节正文（Markdown 格式），直接从标题和正文开始，禁止任何开场白或字数统计元数据标注\n\n"
            f"{REASONING_CHINESE_DEFENSE_PROMPT}\n"
        )

        # 字数预算：注入结构配额块（_allocate_section_budgets 等价移植）
        if chapter_budget > 0:
            if ch_seq > 0:
                hierarchy = _parse_outline_hierarchy(outline_md, ch_seq)
                allocation = _allocate_section_budgets(hierarchy, chapter_budget)
                quota_block = _build_section_quota_block(hierarchy, allocation)
                if quota_block:
                    prompt += f"\n{quota_block}\n"

        lock_block = self._build_cross_chapter_lock(outline_md, predecessor_chapters)
        if lock_block:
            prompt += f"\n{lock_block}\n"

        system = _build_writing_system_prompt(
            self.report_type, 0, 0, writing_hint,
            chapter_budget=chapter_budget,
            is_summary=is_summary,
            chapter_title=chapter_title,
            topic=topic,
        )

        return prompt, system

    # ── 修订执行 ──
    def modify_chapter(self, original_content: str, instruction: str,
                       chapter_budget: int = 0, auto_compress: bool = False,
                       chapter_title: str = "", topic: str = "") -> str:
        """按用户修改意见对章节做局部修改。"""
        prompt, system = self._build_modify_args(
            original_content, instruction, chapter_budget,
            report_type=self.report_type,
            chapter_title=chapter_title,
            topic=topic,
        )
        if auto_compress:
            res = self.llm.chat(prompt, system_prompt=system, temperature=0.15,
                                frequency_penalty=0.5,
                                presence_penalty=0.25,
                                top_p=0.8)
        else:
            res = self.llm.chat(prompt, system_prompt=system, temperature=TEMPERATURE_MODIFY,
                                frequency_penalty=FREQUENCY_PENALTY,
                                presence_penalty=PRESENCE_PENALTY,
                                top_p=TOP_P)
        return normalize_chapter_markdown(res)

    def _build_modify_args(self, original_content: str, instruction: str,
                           chapter_budget: int,
                           report_type: str = "",
                           chapter_title: str = "",
                           topic: str = "") -> tuple:
        """返回 (prompt, system)。含技术分析规则穿透。"""
        original_words = _count_chinese_chars(original_content)

        if any(w in instruction for w in ['字', '压缩', '扩写', '缩短', '扩充']):
            word_constraint = "严格按用户指定的字数约束执行"
        elif chapter_budget > 0:
            lo = int(chapter_budget * 0.9)
            hi = int(chapter_budget * 1.1)
            word_constraint = (
                f"当前章节预算{chapter_budget:,}字，修改后字数控制在 {lo:,}–{hi:,} 字之间"
                f"（预算 ±10%）。请据此调整内容详略，不得超出此范围。"
            )
        else:
            word_constraint = f"保持原文约{original_words}字的规模"

        system = _MODIFY_SYSTEM_PROMPT.format(word_constraint=word_constraint)

        tech_rules = _build_tech_analysis_rules(report_type, chapter_title or "", topic or "")
        if tech_rules:
            system += "\n\n" + tech_rules

        prompt = (
            f"## 原文\n{original_content}\n\n"
            f"## 修改意见\n{instruction}\n\n"
            f"请根据上述修改意见，返回修改后的完整章节内容：\n\n"
            f"{REASONING_CHINESE_DEFENSE_PROMPT}"
        )
        return prompt, system

    def _build_expert_review_args(self, chapter_title: str, chapter_text: str,
                                   mode: str = "fast") -> tuple[str, str]:
        """构建专家审阅 prompt 与 system_prompt。"""
        prompt = (
            f"## 待审阅章节标题\n{chapter_title or '当前章节'}\n\n"
            f"## 待审阅正文内容\n{chapter_text}\n\n"
            f"{REASONING_CHINESE_DEFENSE_PROMPT}\n\n"
            f"请按要求进行专业诊断并严格输出规定的 JSON 结果。"
        )
        if mode == "fast":
            system = FAST_REVIEW_SYSTEM_PROMPT
        elif mode == "compliance":
            system = COMPLIANCE_REVIEW_SYSTEM_PROMPT
        elif mode in ("numeric", "numerical"):
            system = NUMERICAL_REVIEW_SYSTEM_PROMPT
        elif mode == "technical":
            system = TECH_REVIEW_SYSTEM_PROMPT
        else:
            system = FULL_EXPERT_REVIEW_SYSTEM_PROMPT
        return prompt, system

    # ── 专家审阅 ──
    def expert_review(self, chapter_title: str, chapter_text: str,
                      mode: str = "fast") -> tuple[str, dict]:
        """对章节进行全维专家诊断或专项审阅。返回 (raw_output, parsed_dict)。"""
        prompt, system = self._build_expert_review_args(chapter_title, chapter_text, mode=mode)
        raw = self.llm.chat(prompt, system_prompt=system, temperature=0.2)
        if mode == "technical":
            parsed = parse_tech_review_result(raw)
        else:
            parsed = parse_expert_review_result(raw)
        return raw, parsed

    # ── 辅助方法 ──
    @staticmethod
    def _parse_chapter_seq(chapter_title: str) -> int:
        """从 '第X章 xxx' 提取章序号。"""
        cn_num_map = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '零': 0,
        }
        m = re.match(r'第([一二三四五六七八九十百零\d]+)章', chapter_title)
        if not m:
            return 0
        num_str = m.group(1)
        if num_str.isdigit():
            return int(num_str)
        result = 0
        if num_str.startswith('十'):
            result = 10
            num_str = num_str[1:]
        for ch in num_str:
            if ch in cn_num_map:
                result += cn_num_map[ch]
        return result if result > 0 else 0

    def _build_prev_context(self, predecessor_chapters: dict) -> str:
        """构建前序章正文。按章节自然升序排列格式化供大模型参考。"""
        if not predecessor_chapters:
            return ""
        def _sort_key(k):
            try:
                return int(k)
            except Exception:
                return 999
        parts = []
        for num, content in sorted(predecessor_chapters.items(), key=lambda item: _sort_key(item[0])):
            if content and str(content).strip():
                parts.append(f"## 第 {num} 章\n{content}")
        return "\n\n---\n\n".join(parts)

    def _build_cross_chapter_lock(self, outline_md: str,
                                  predecessor_chapters: dict) -> str:
        """跨章方案锁定约束块。"""
        if not predecessor_chapters:
            return ""

        lines = outline_md.split('\n')
        ch_pattern = re.compile(r'^#\s+第([一二三四五六七八九十百零\d]+)章')

        def _extract_ch_seq(line: str) -> int:
            m = ch_pattern.match(line)
            if not m:
                return 0
            return self._parse_chapter_seq(f"第{m.group(1)}章")

        comparison_points = {}
        seen_subtitles = set()
        current_ch = 0
        current_section = ""

        for i, line in enumerate(lines):
            ch_m = ch_pattern.match(line)
            if ch_m:
                current_ch = _extract_ch_seq(line)
                continue

            if current_ch not in predecessor_chapters and str(current_ch) not in predecessor_chapters:
                continue

            if line.startswith('## '):
                current_section = line.strip('# ').strip()
            elif line.startswith('### '):
                current_section = line.strip('# ').strip()

            if line.startswith('###') and ('比选' in line or '比较' in line) and '（' in line:
                m = re.search(r'（(.+?)）', line)
                instruction = m.group(1) if m else ""
                sub_title = re.sub(r'^#+\s*', '', line).strip()
                if sub_title not in seen_subtitles:
                    seen_subtitles.add(sub_title)
                    comparison_points.setdefault(current_ch, []).append({
                        'section': current_section,
                        'sub_title': sub_title,
                        'instruction': instruction,
                    })
                continue

            if line.startswith('###') and '比选' in line and '（' not in line:
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j].strip()
                    if not next_line:
                        continue
                    if '（' in next_line:
                        m = re.search(r'（(.+?)）', next_line)
                        instruction = m.group(1) if m else ""
                        sub_title = re.sub(r'^#+\s*', '', line).strip()
                        if sub_title not in seen_subtitles:
                            seen_subtitles.add(sub_title)
                            comparison_points.setdefault(current_ch, []).append({
                                'section': current_section,
                                'sub_title': sub_title,
                                'instruction': instruction,
                            })
                        break
                    if next_line.startswith('#'):
                        break

        if not comparison_points:
            return ""

        locks = ["\n## 🔒 跨章方案锁定（全局约束）"]
        locks.append(
            "\n以下前序章节已完成多方案比选，各项推荐方案已经锁定。"
            "**本章所有内容必须在已锁定的推荐方案基础上展开，不得重新比较或引入新的备选方案：**\n"
        )

        for ch_num in sorted(comparison_points.keys()):
            ch_title = f"第{ch_num}章"
            for line in lines:
                m = ch_pattern.match(line)
                if m and _extract_ch_seq(line) == ch_num:
                    ch_title = line.strip('# ').strip()
                    break

            for pt in comparison_points[ch_num]:
                section_tag = f"{ch_title} → {pt['section']}" if pt['section'] else ch_title
                locks.append(
                    f"- **{section_tag}**：已完成{pt['instruction']}，"
                    f"推荐方案已锁定。**不得重新比较或引入其他备选方案。**"
                )

        locks.append(
            "\n请以前序锁定方案为前提，继续撰写本章内容。"
            "本章若有独立的比选（不在锁定列表中），可按大纲要求正常进行。"
        )

        return '\n'.join(locks)


# ═══════════════════════════════════════════════════════════════
# 技术审阅结果解析（v1.0.4）
# ═══════════════════════════════════════════════════════════════

_VALID_TECH_REVIEW_STATUSES = ("通过", "需补充", "不适用")


def parse_tech_review_result(raw_output: str) -> dict:
    """解析并校验技术审阅 LLM 输出。返回结构化 dict。"""
    if not raw_output or not raw_output.strip():
        return {
            "status": "不适用",
            "reason": "",
            "details": "",
            "suggestions": "",
            "data_gap_checklist": [],
            "parse_error": "Empty response from LLM",
        }

    result = {
        "status": "",
        "reason": "",
        "details": "",
        "suggestions": "",
        "data_gap_checklist": [],
        "parse_error": None,
    }

    text = raw_output.strip()

    status_match = re.search(r'(?:状态|校核结果|结论)[：:]\s*(通过|需补充|不适用)', text)
    if not status_match:
        for status in _VALID_TECH_REVIEW_STATUSES:
            if status in text[:200]:
                result["status"] = status
                break
    else:
        result["status"] = status_match.group(1)

    if result["status"] not in _VALID_TECH_REVIEW_STATUSES:
        result["parse_error"] = f"Unrecognized status: {result['status'] or 'missing'}"
        result["status"] = "不适用"
        return result

    reason_match = re.search(r'(?:原因|问题)[：:]\s*(.+?)(?:\n|$)', text)
    if reason_match:
        result["reason"] = reason_match.group(1).strip()

    details_match = re.search(r'(?:详情|详细|发现)[：:]\s*(.+?)(?:\n\n|\n(?:建议|资料|清单)|$)', text, re.DOTALL)
    if details_match:
        result["details"] = details_match.group(1).strip()

    sugg_match = re.search(r'(?:建议|改进建议)[：:]\s*(.+?)(?:\n\n|\n(?:资料|清单|$)|$)', text, re.DOTALL)
    if sugg_match:
        result["suggestions"] = sugg_match.group(1).strip()

    if result["status"] == "需补充":
        checklist_match = re.search(r'(?:资料清单|缺失资料|需补充资料)[：:]\s*(.+?)(?:\n\n|$)', text, re.DOTALL)
        if checklist_match:
            items_text = checklist_match.group(1).strip()
            items = re.findall(r'[-*\d.]\s*(.+?)(?:\n|$)', items_text)
            result["data_gap_checklist"] = [item.strip() for item in items if item.strip()]
        if not result["data_gap_checklist"]:
            result["parse_error"] = "Status is '需补充' but no data gap checklist found"

    return result


# ═══════════════════════════════════════════════════════════════
# 全维专家审阅结果解析与统一诊断
# ═══════════════════════════════════════════════════════════════

_VALID_EXPERT_STATUSES = ("通过", "需补充", "风险警告")


def parse_expert_review_result(raw_output: str) -> dict:
    """解析并校验全维专家诊断或专项审查 LLM 输出。返回统一结构化 dict。"""
    default_res = {
        "status": "通过",
        "score": 85,
        "summary": "",
        "issues": [],
        "numerical_checks": [],
        "data_gap_checklist": [],
        "suggestions": "",
        "raw": raw_output or "",
        "parse_error": None,
    }
    if not raw_output or not raw_output.strip():
        default_res["status"] = "需补充"
        default_res["score"] = 0
        default_res["parse_error"] = "Empty review response from LLM"
        return default_res

    text = raw_output.strip()

    # 1. 尝试从 ```json ... ``` 或裸 JSON 中提取
    json_str = None
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        json_str = json_match.group(1).strip()
    elif text.startswith("{") and text.endswith("}"):
        json_str = text
    else:
        brace_match = re.search(r'(\{[\s\S]*\})', text)
        if brace_match:
            json_str = brace_match.group(1).strip()

    if json_str:
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                # 状态
                status_raw = str(parsed.get("status", "通过")).strip()
                if status_raw in _VALID_EXPERT_STATUSES:
                    status = status_raw
                elif "补充" in status_raw:
                    status = "需补充"
                elif "风险" in status_raw or "警告" in status_raw or "不通过" in status_raw or "差" in status_raw:
                    status = "风险警告"
                else:
                    status = "通过"

                # 评分
                raw_score = parsed.get("score")
                try:
                    score = int(raw_score)
                    score = max(0, min(100, score))
                except (ValueError, TypeError):
                    if status == "通过":
                        score = 88
                    elif status == "需补充":
                        score = 72
                    else:
                        score = 55

                summary = str(parsed.get("summary", "")).strip()

                # 问题清单
                raw_issues = parsed.get("issues", [])
                issues = []
                if isinstance(raw_issues, list):
                    for idx, it in enumerate(raw_issues):
                        if isinstance(it, dict):
                            sev = str(it.get("severity", "suggestion")).lower()
                            if sev not in ("error", "warning", "suggestion"):
                                if "错" in sev or "高" in sev or "严重" in sev or "err" in sev:
                                    sev = "error"
                                elif "警" in sev or "中" in sev or "warn" in sev:
                                    sev = "warning"
                                else:
                                    sev = "suggestion"
                            issues.append({
                                "id": str(it.get("id", f"ISSUE-{idx+1}")),
                                "severity": sev,
                                "category": str(it.get("category", "综合诊断")),
                                "message": str(it.get("message", "")),
                                "location": str(it.get("location", "")),
                                "quote": str(it.get("quote", "")).strip(),
                                "suggestion": str(it.get("suggestion", "")),
                            })

                # 数值核验项
                raw_num = parsed.get("numerical_checks", [])
                num_checks = []
                if isinstance(raw_num, list):
                    for it in raw_num:
                        if isinstance(it, dict):
                            st = str(it.get("status", "normal")).lower()
                            if st not in ("normal", "abnormal", "pending"):
                                if "异" in st or "矛盾" in st or "错" in st or "abnormal" in st:
                                    st = "abnormal"
                                elif "待" in st or "缺" in st or "pend" in st:
                                    st = "pending"
                                else:
                                    st = "normal"
                            num_checks.append({
                                "parameter": str(it.get("parameter", "")),
                                "extracted_value": str(it.get("extracted_value", "")),
                                "status": st,
                                "note": str(it.get("note", "")),
                            })

                # 缺失资料清单
                raw_gaps = parsed.get("data_gap_checklist", [])
                gaps = []
                if isinstance(raw_gaps, list):
                    gaps = [str(g).strip() for g in raw_gaps if str(g).strip()]

                # 修改建议
                suggestions = parsed.get("suggestions", "")
                if isinstance(suggestions, list):
                    suggestions = "\n".join(str(s) for s in suggestions)
                else:
                    suggestions = str(suggestions).strip()

                return {
                    "status": status,
                    "score": score,
                    "summary": summary,
                    "issues": issues,
                    "numerical_checks": num_checks,
                    "data_gap_checklist": gaps,
                    "suggestions": suggestions,
                    "raw": raw_output,
                    "parse_error": None,
                }
        except Exception:
            pass

    # 2. 纯文本降级兜底解析
    status = "通过"
    for st in ("风险警告", "需补充", "通过"):
        if st in text[:200]:
            status = st
            break

    score = 85 if status == "通过" else (70 if status == "需补充" else 50)
    score_m = re.search(r'(?:【?(?:得分|评分|分数)】?)[：:\s]*(\d+)', text)
    if score_m:
        try:
            score = max(0, min(100, int(score_m.group(1))))
        except Exception:
            pass

    summary = ""
    sum_m = re.search(r'(?:【?(?:评价|结论|摘要|原因说明)】?)[：:\s]*(.+?)(?:\n\n|\n[#【]|$)', text, re.DOTALL)
    if sum_m:
        summary = sum_m.group(1).strip()

    suggestions = ""
    sug_m = re.search(r'(?:【?(?:修改建议|建议|指引)】?)[：:\s]*(.+?)(?:\n\n|\n[#【]|$)', text, re.DOTALL)
    if sug_m:
        suggestions = sug_m.group(1).strip()

    gaps = []
    gap_m = re.search(r'(?:【?(?:缺失资料|需补充资料|资料清单|缺失资料清单)】?)[：:\s]*(.+?)(?:\n\n|\n[#【]|$)', text, re.DOTALL)
    if gap_m:
        gap_items = re.findall(r'[-*\d.]\s*(.+?)(?:\n|$)', gap_m.group(1))
        gaps = [item.strip() for item in gap_items if item.strip()]

    return {
        "status": status,
        "score": score,
        "summary": summary or text[:120],
        "issues": [],
        "numerical_checks": [],
        "data_gap_checklist": gaps,
        "suggestions": suggestions,
        "raw": raw_output,
        "parse_error": None,
    }


def expert_review_chapter(chapter_title: str, chapter_text: str,
                          report_type: str = "", review_mode: str = "fast",
                          llm=None) -> tuple[str, dict]:
    """对章节文本进行专家审查并解析返回结构化结果。"""
    if llm is None:
        raise ValueError("llm instance is required")
    writer = ChapterWriter(llm, report_type=report_type)
    return writer.expert_review(chapter_title, chapter_text, mode=review_mode)
