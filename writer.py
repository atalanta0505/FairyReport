"""
Writer v1.0.5 — Chapter writing, modification-execution, and writing-hint generation
- Per-chapter writing: writing_hint is auto-injected into the system prompt (not exposed to the user)
- New modify_chapter(): apply user modification instructions locally (preserve original word count)
- New generate_hint(): auto-generate writing_hint and write it back
- Removed global_modify(): v1.0.2 uses Step 4 "Review Full Text" instead
- v1.0.4: technical analysis framework and insufficient-data rules injected for tech chapters
"""
from config import (
    TEMPERATURE_WRITING, TEMPERATURE_MODIFY, TEMPERATURE_HINT,
    get_chapter_word_budget,
    get_template_notes, FREQUENCY_PENALTY, PRESENCE_PENALTY, TOP_P,
)

# ═══════════════════════════════════════════════════════════════
# Technical analysis rules builder (v1.0.4)
# ═══════════════════════════════════════════════════════════════

def _chapter_has_tech_keyword(chapter_title: str) -> bool:
    """Check if chapter title contains any tech-related keyword."""
    from config import TECH_CHAPTER_KEYWORDS
    if not chapter_title:
        return False
    return any(kw in chapter_title for kw in TECH_CHAPTER_KEYWORDS)


def _is_tech_analysis_applicable(report_type: str, chapter_title: str,
                                  topic: str = "") -> bool:
    """Determine whether technical analysis enhancement rules should be applied.

    Decision logic:
    1. If report_type is in TECH_ANALYSIS_ALWAYS_REPORT_TYPES -> enable when chapter keywords match
    2. If report_type is in TECH_ANALYSIS_CONDITIONAL_REPORT_TYPES -> enable only when chapter keywords match AND topic involves technology
    3. Otherwise -> enable when chapter keywords match
    """
    from config import (
        TECH_ANALYSIS_ALWAYS_REPORT_TYPES,
        TECH_ANALYSIS_CONDITIONAL_REPORT_TYPES,
    )

    # Chapter keyword check: cheapest gate, must pass first
    if not _chapter_has_tech_keyword(chapter_title):
        return False

    # Always-enabled report types
    if report_type in TECH_ANALYSIS_ALWAYS_REPORT_TYPES:
        return True

    # Conditional report types — require topic to involve technology as well
    if report_type in TECH_ANALYSIS_CONDITIONAL_REPORT_TYPES:
        return bool(topic) and any(kw in topic for kw in [
            "工艺", "技术", "设备", "工程", "产线", "制造",
            "生产", "数字化", "智能化", "能源", "环保",
        ])

    # Other report types: only if chapter title contains tech keyword
    # (which passed the gate above)
    return True


def _build_tech_analysis_rules(report_type: str, chapter_title: str,
                                topic: str = "") -> str:
    """Build the tech analysis rules block to inject into the writing system prompt.

    Returns empty string if tech analysis is not applicable to this chapter.
    """
    if not _is_tech_analysis_applicable(report_type, chapter_title, topic):
        return ""

    from config import TECH_WRITING_FRAMEWORK, TECH_INSUFFICIENT_DATA_RULES
    return TECH_WRITING_FRAMEWORK + "\n\n" + TECH_INSUFFICIENT_DATA_RULES


# ── Chapter writing system prompt ──
_BASE_WRITING_PROMPT = """\
你是资深工程咨询报告撰写专家。"""


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

    # Core rules
    rules = """
核心规则：
0. **禁止开场白**：不要输出任何"好的"、"作为专家"、"我将"等确认语或自我介绍，直接从章节标题和正文开始。
1. **大纲锁定**：严格按大纲中的标题文字和层级写作，绝不修改任何标题
2. **引用格式**：引用时只能使用上方「参考资料」中实际出现的来源标签。项目资料使用【源:文件名】，网页搜索结果使用【网:标题】，AI 自有知识使用 [Z]。**严禁编造不存在的标签**——如果某个信息来源不在上方搜索结果中，使用 [Z] 标注即可。导出时系统将统一生成参考文献编号。
3. **逻辑连贯**：如果前文已有相关数据或结论，请在基础上自然衔接
4. **专业表达**：使用工程咨询行业的标准术语和表述方式
5. **内容充实**：每节/小节都要有实质性内容，不要空洞"""

    # Word-count constraint
    if total_words > 0 and total_chapters > 0:
        rules += f"\n6. **篇幅建议**：全篇目标{total_words:,}字，共{total_chapters}章。每章有建议字数（见规则7），请尽量控制在预算范围内。"

    # v1.0.2: per-chapter budget written into system prompt directly (more constraining than user-prompt suffix)
    if chapter_budget > 0:
        lo = int(chapter_budget * 0.9)
        hi = int(chapter_budget * 1.1)
        if is_summary:
            rules += f"\n7. **本章字数**：本章为综述/总结性章节，预算 **{chapter_budget:,} 字**。请精炼概括，控制在 {lo:,}–{hi:,} 字范围内。"
        else:
            rules += f"\n7. **本章字数建议**：本章建议 **{chapter_budget:,} 字**（仅计正文，标题不占字数）。每个小节有参考配额（见 user prompt 底部结构框架），请按配额逐节分配内容密度。"

    # Template conventions (injected from the report type template JSON `notes` field)
    template_notes = get_template_notes(report_type)
    rule_num = 8 if chapter_budget > 0 else 7
    if template_notes:
        rules += f"\n{rule_num}. **模板规范**：{template_notes}"

    # v1.0.4: inject technical analysis rules when applicable
    tech_rules = _build_tech_analysis_rules(report_type, chapter_title or "", topic or "")
    if tech_rules:
        rules += "\n\n" + tech_rules

    # v1.0.2: writing_hint injected into system prompt
    if writing_hint:
        rules += f"\n\n本章编写提示：{writing_hint}"

    return base + "\n" + rules


# ── Writing-hint generation prompt (v1.0.2 §6.3) ──
_HINT_SYSTEM_PROMPT = """\
你是工程咨询报告审校专家。请为以下章节撰写一段简短的编写提示。
提示需包含：
1. 该章应覆盖的核心内容（严格参照大纲中该章的子标题结构）
2. 基于编写顺序的衔接要点（前序章已提供提示词供参考）
3. 推荐的写作风格或注意事项

**硬性约束（最高优先级）**：
- **所有章节都必须严格按照大纲中的子标题层级和标题文字编写，不得使用"浓缩""一页纸""归纳总结""自由发挥"等鼓励偏离大纲结构的措辞**
- 大纲提供的每个 ## 和 ### 子标题都是必须编写的章节内容，不得合并、跳过或自定义标题
- 写作风格建议仅涉及语气、详略、数据引用等，不得改变大纲规定的标题结构

如果提供了「用户修改意图」和「现有提示词」，请根据用户意图调整现有提示词的方向，而非从头生成：
- 保留现有提示词中与用户意图不冲突的部分
- 按用户意图调整内容侧重、篇幅、或写法风格
- 重新生成衔接要点（因前序章可能有变化）

提示末尾必须包含一行可执行指令：
- 当前章不是写作顺序第1顺位时：「请根据 ①本章提示词 ②大纲及模板 ③前序章.md 文件来编写本章，字数控制在预算范围内。」
- 当前章是写作顺序第1顺位时：「请根据 ①本章提示词 ②大纲及模板 来编写本章，字数控制在预算范围内。」

限 300 字以内，用中文直接输出，不要任何格式标记。"""


# ── Modification-execution prompt (v1.0.2 §6.5, deprecated — replaced by hint-generation pipeline) ──
_MODIFY_SYSTEM_PROMPT = """\
你是工程咨询报告修改专家。根据用户给出的修改意见，对原文章节进行**局部、精确**的修改。

要求：
1. **局部修改**：只修改用户指令中提到的部分，未提到的文字、数据、结构保持完全不变
2. **字数约束**：{word_constraint}。**"重写"不等于"精简"——重写时必须保持与原文相当的篇幅和详细程度，不得无故删减内容。**
3. **引用保持**：原文中的【源:xxx】、【网:xxx】和 [Z] 引用标记请保持使用状态，导出时系统将统一转换为数字编号
4. **标题不动**：不得修改任何标题
5. **格式一致**：保持原有的 Markdown 格式和层级结构

返回修改后的**完整章节**（Markdown 格式），而非只返回修改的片段。
**必须输出完整章节，不得省略任何段落。**"""


def _count_chapters(outline_md: str) -> int:
    """Count chapter headings in outline Markdown."""
    import re
    matches = re.findall(r'^#\s+第.+章', outline_md, re.MULTILINE)
    return len(matches) or 1


def _trim_outline_to_position(outline_md: str, allowed_seqs: list) -> str:
    """Trim the outline, keeping only chapters whose seqs are in `allowed_seqs` (writing-order position <= current chapter).

    Prevents the hint-generation LLM from hallucinating references to chapters that have not yet been written.
    allowed_seqs: list of allowed chapter seqs, e.g. [1, 2, 3, 7].
    """
    import re
    lines = outline_md.split('\n')
    result = []
    in_chapter = True   # Keep the leading content (foreword, etc.) at the start
    current_seq = 0
    # Match chapter heading: "第N章" (Chinese/Arabic) or "# N." format
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
            # This is a chapter heading line
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
    """Count effective characters in an engineering report: Chinese chars + full-width punctuation + CJK spaces."""
    import re
    # \u4e00-\u9fff: CJK | \u3000-\u303f: CJK punctuation | \uff00-\uffef: full-width ASCII/punctuation
    return len(re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', text))


def _strip_markdown_headings(text: str) -> str:
    """Remove Markdown heading lines (lines starting with #), keep only body text for word counting."""
    import re
    return re.sub(r'^#{1,6}\s+.*$', '', text, flags=re.MULTILINE)


def _count_content_chars(text: str) -> int:
    """Count Chinese characters in the body (excluding Markdown headings)."""
    return _count_chinese_chars(_strip_markdown_headings(text))


# ── Outline hierarchy parsing & per-section word budget allocation ──

def _parse_outline_hierarchy(outline_md: str, chapter_seq: int) -> dict:
    """Parse the H2/H3 hierarchy of the given chapter in the outline.

    Returns: {
        "chapter_title": "第二章 现状分析与评价",
        "h2_sections": [
            {"title": "2.1 区域发展现状", "level": 2,
             "h3_subsections": [
                 {"title": "2.1.1 区位与交通条件", "level": 3},
                 ...
             ]},
            ...
        ]
    }
    """
    import re
    lines = outline_md.split('\n')
    result = {"chapter_title": "", "h2_sections": []}

    # Chinese numeral mapping (1-30)
    _cn_nums = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
                '二十一', '二十二', '二十三', '二十四', '二十五', '二十六', '二十七', '二十八', '二十九', '三十']
    cn_num = _cn_nums[chapter_seq] if chapter_seq < len(_cn_nums) else str(chapter_seq)

    # Match chapter heading: support "第N章" (Arabic), "第二章" (Chinese), "# N." three formats
    ch_pattern = re.compile(
        r'^#\s+(?:第\s*(?:' + str(chapter_seq) + r'|' + cn_num + r')\s*章|' + str(chapter_seq) + r'[\.\s])'
    )
    in_chapter = False
    current_h2 = None

    for line in lines:
        # Found the target chapter
        if ch_pattern.match(line):
            in_chapter = True
            result["chapter_title"] = re.sub(r'^#\s+', '', line).strip()
            continue
        if in_chapter and re.match(r'^#\s+', line) and not line.startswith('##'):
            break  # Next chapter started

        if not in_chapter:
            continue

        # H2: starts with ##
        if re.match(r'^##\s+', line):
            title = re.sub(r'^##\s+', '', line).strip()
            current_h2 = {"title": title, "level": 2, "h3_subsections": []}
            result["h2_sections"].append(current_h2)

        # H3: starts with ###
        elif re.match(r'^###\s+', line) and current_h2 is not None:
            title = re.sub(r'^###\s+', '', line).strip()
            current_h2["h3_subsections"].append({"title": title, "level": 3})

    return result


def _allocate_section_budgets(hierarchy: dict, chapter_budget: int) -> dict:
    """Allocate word budgets to each H3 subsection.

    Strategy:
    - Split chapter_budget evenly across H2 sections
    - Within each H2, split evenly across H3 subsections
    - Round results to the nearest 50 characters
    """
    h2_sections = hierarchy["h2_sections"]
    if not h2_sections:
        return {"h2_sections": [], "total_allocated": 0}

    # Total number of H3 subsections
    total_h3 = sum(len(h2["h3_subsections"]) for h2 in h2_sections)
    if total_h3 == 0:
        # No H3, split evenly by H2
        per_h2 = max(50, chapter_budget // len(h2_sections))
        for h2 in h2_sections:
            h2["budget"] = per_h2
        return {"h2_sections": h2_sections, "total_allocated": per_h2 * len(h2_sections)}

    # Split H3 evenly, round to 50
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

    # Allocate the remainder to the first H2
    remainder = chapter_budget - total
    if remainder > 0 and h2_sections:
        h2_sections[0]["budget"] += remainder
        if h2_sections[0]["h3_subsections"]:
            h2_sections[0]["h3_subsections"][0]["budget"] += remainder

    return {"h2_sections": h2_sections, "total_allocated": chapter_budget}


def _build_section_quota_block(hierarchy: dict, allocation: dict) -> str:
    """Generate a "structure quota" prompt block."""
    h2_sections = allocation.get("h2_sections", [])
    if not h2_sections:
        return ""

    chapter_title = hierarchy.get("chapter_title", "")

    lines = [
        f"\n## 📐 结构参考（篇幅建议）",
        f"「{chapter_title}」建议 **{allocation['total_allocated']:,} 字**（仅计正文，标题不计入）。",
        f"以下为各小节的参考字数，请按比例分配内容密度：\n",
    ]

    for i, h2 in enumerate(h2_sections):
        h3s = h2["h3_subsections"]
        h3_list = "、".join(h3["title"] for h3 in h3s) if h3s else "（无小节）"
        if h3s:
            lines.append(f"- **{h2['title']}**（约{h2['budget']:,} 字，含 {len(h3s)} 小节：{h3_list}）")
            for h3 in h3s:
                lines.append(f"  · {h3['title']}：约{h3['budget']:,} 字")
        else:
            lines.append(f"- **{h2['title']}**：约{h2['budget']:,} 字")

    lines.append(f"\n**总字数建议约 {allocation['total_allocated']:,} 字，标题不计数，请尽量控制在预算附近。**")

    return "\n".join(lines)


def check_chapter_word_limit(content: str, report_type: str, chapter_title: str, ch_seq: int):
    """Post-validation: whether chapter word count is within budget. Returns (is_over, wc, budget, warning_msg).

    Thresholds (v1.0.2 tightened; counter now includes full-width punctuation):
    - <85% of budget: under-filled, suggest enriching
    - 85%-115%: meets target
    - >115% of budget: over budget, requires auto-compression
    """
    from config import get_chapter_word_budget
    budget = get_chapter_word_budget(report_type, ch_seq)
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


class ChapterWriter:
    def __init__(self, llm, report_type: str = "", total_words: int = 0):
        self.llm = llm
        self.report_type = report_type
        self.total_words = total_words

    # ── Writing-hint generation ──
    def generate_hint(self, chapter_title: str, chapter_seq: int,
                      outline_md: str, writing_order: list,
                      predecessor_hints: dict = None,
                      report_name: str = "",
                      user_instruction: str = "",
                      existing_hint: str = "") -> str:
        """Generate the writing hint for the given chapter.

        predecessor_hints: {ch_seq: hint_text} — hints of predecessor chapters (those preceding
            the current one in writing order). When the current chapter is at position 1 in
            writing order, predecessor_hints is empty.
        user_instruction: user's modification intent (non-empty triggers modification mode,
            adjusting the existing hint rather than regenerating from scratch).
        existing_hint: the current chapter's existing hint (baseline for modification mode).
        """
        # v1.0.2: trim outline to keep only chapters with writing-order position <= current chapter,
        # preventing the LLM from referencing chapters that have not yet been written
        pos = writing_order.index(chapter_seq)
        trimmed_outline = _trim_outline_to_position(outline_md, writing_order[:pos + 1])

        report_label = f" [{self.report_type}]" if self.report_type else ""
        # Writing-order information
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

        # Modification mode: inject user intent and existing hint
        if user_instruction:
            prompt += (
                f"⚠️ 修改模式：请根据用户意图调整现有提示词。\n"
                f"用户修改意图：{user_instruction}\n"
                f"现有提示词：{existing_hint or '（无）'}\n"
            )
            prompt += "\n"

        prompt += f"请为「{chapter_title}」撰写编写提示："
        hint = self.llm.chat(prompt, system_prompt=_HINT_SYSTEM_PROMPT,
                             temperature=TEMPERATURE_HINT).strip()
        return hint

    # ── Chapter writing (non-streaming) ──
    def write_chapter(self, chapter_title: str, outline_md: str,
                      predecessor_chapters: dict, rag_context: str,
                      topic: str, writing_hint: str = "",
                      report_name: str = "") -> str:
        """Single-pass chapter writing. writing_hint is injected into the system prompt."""
        prompt, system = self._build_chapter_write_args(
            chapter_title, outline_md, predecessor_chapters, rag_context, topic, writing_hint,
            report_name=report_name
        )
        return self.llm.chat(prompt, system_prompt=system, temperature=TEMPERATURE_WRITING,
                            frequency_penalty=FREQUENCY_PENALTY,
                            presence_penalty=PRESENCE_PENALTY,
                            top_p=TOP_P)

    # ── Chapter writing (streaming) ──
    def write_chapter_stream(self, chapter_title: str, outline_md: str,
                              predecessor_chapters: dict, rag_context: str,
                              topic: str, callback=None, writing_hint: str = "",
                              report_name: str = "") -> str:
        """Streaming single-chapter writing. writing_hint is injected into the system prompt."""
        prompt, system = self._build_chapter_write_args(
            chapter_title, outline_md, predecessor_chapters, rag_context, topic, writing_hint,
            report_name=report_name
        )
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        return self.llm.chat_stream(messages, temperature=TEMPERATURE_WRITING,
                                    callback=callback,
                                    frequency_penalty=FREQUENCY_PENALTY,
                                    presence_penalty=PRESENCE_PENALTY,
                                    top_p=TOP_P)

    # ── Chapter generation pipeline with automatic word-count correction ──
    def write_chapter_with_control(self, chapter_title: str, outline_md: str,
                                    predecessor_chapters: dict, rag_context: str,
                                    topic: str, callback=None, writing_hint: str = "",
                                    max_retries: int = 2,
                                    report_name: str = "") -> str:
        """First-pass streaming generation, then automatic validation + silent compression/expansion, up to 2 rounds.

        Pipeline:
          1. Streaming generation (user experience unchanged)
          2. Accurate character-count validation → within [85%, 115%] → return directly
          3. Off-target → call modify_chapter to compress/expand
          4. Brake: if two consecutive modify rounds change word count by <5% → exit, no more retries
        """
        # First pass: streaming generation
        content = self.write_chapter_stream(
            chapter_title, outline_md, predecessor_chapters,
            rag_context, topic, callback, writing_hint,
            report_name=report_name
        )

        ch_seq = self._parse_chapter_seq(chapter_title)
        budget = get_chapter_word_budget(self.report_type, ch_seq) if ch_seq > 0 else 0
        if budget <= 0:
            return content  # No budget defined, skip validation

        prev_wc = _count_chinese_chars(content)
        for attempt in range(max_retries):
            is_over, wc, _, msg = check_chapter_word_limit(
                content, self.report_type, chapter_title, ch_seq
            )
            if not is_over:
                return content  # Within target ✓

            # Brake: if two consecutive modify rounds changed word count by <5%
            if attempt > 0 and abs(wc - prev_wc) < prev_wc * 0.05:
                return content

            prev_wc = wc

            # Build auto-correction instruction
            if wc > budget * 1.15:
                target = int(budget * 1.05)
                instruction = (
                    f"⚠️ Auto-compress: current {wc:,} chars, target {target:,} chars.\n"
                    f"[Deletion priority] 1. ornamental adverbs/transition filler → 2. repetitive background → 3. non-core examples\n"
                    f"[Preserve] technical parameters, financial metrics, policy basis, core conclusions — do not touch.\n"
                    f"Merge long sentences into shorter ones, compress ~{int((wc - target) / wc * 100)}% of the text."
                )
            else:
                target = int(budget * 0.95)
                instruction = (
                    f"⚠️ Auto-expand: current {wc:,} chars, target {target:,} chars. "
                    f"Supplement causal reasoning, data comparisons, or implementation paths in core subsections; "
                    f"add ~{int((target - wc) / budget * 100)}% more content. Do NOT add new case studies or new subsections."
                )

            # Silent compress/expand (auto-compress mode: low temperature, high penalty, low top_p)
            # FRL-009: carry tech analysis rules through to prevent fabricated parameters
            content = self.modify_chapter(content, instruction, chapter_budget=budget,
                                          auto_compress=True,
                                          chapter_title=chapter_title,
                                          topic=topic)

        return content

    # ── Chapter writing helpers: build Prompt / System ──
    def _build_chapter_write_args(self, chapter_title: str, outline_md: str,
                                   predecessor_chapters: dict, rag_context: str,
                                   topic: str, writing_hint: str = "",
                                   report_name: str = "") -> tuple:
        """Return (prompt, system).

        Shared by write_chapter / write_chapter_stream.
        predecessor_chapters: only includes chapters that precede the current one in writing order.
        """
        prev_context = self._build_prev_context(predecessor_chapters)

        # v1.0.2: separate project name and industry direction display — project name is the
        # report's core identifier, industry direction (topic) is only a retrieval label;
        # the two are not conflated
        report_label = f"## 项目名称\n{report_name}\n\n## 产业方向\n{topic}" if report_name else f"## 项目主题\n{topic}"

        prompt = (
            f"{report_label}\n\n"
            f"## 完整大纲 [{self.report_type}]\n{outline_md}\n\n"
            f"## 当前章节\n请编写「{chapter_title}」的正文内容\n\n"
        )

        if prev_context:
            prompt += f"## 前文已完成章节（供参考衔接）\n{prev_context}\n\n"

        if rag_context and "无相关参考资料" not in rag_context:
            prompt += f"## 参考资料（RAG 检索结果）\n{rag_context}\n\n"

        prompt += (
            f"## 写作要求\n"
            f"- **硬性约束：必须严格按照上方完整大纲中「{chapter_title}」的所有子标题（##、###、####…）及其标题文字编写，一个子标题不少、不跳过、不自创标题**\n"
            f"- 对事实性陈述插入引用标记：**只能使用上方「参考资料」中实际出现的标签**。项目资料使用【源:文件名】，网页资料使用【网:标题】，AI 自有知识使用 [Z]。严禁编造不存在的【源:xxx】或【网:xxx】标签\n"
            f"- 请输出完整的章节正文（Markdown 格式）\n"
            f"- 禁止输出任何开场白、确认语、角色介绍，直接从标题和正文开始\n"
            f"- **禁止在章节末尾自作主张添加「本章正文字数」等元数据标注**\n"
        )

        # v1.0.2: cross-chapter plan lock — previous-chapter comparison results are globally locked
        lock_block = self._build_cross_chapter_lock(outline_md, predecessor_chapters)
        if lock_block:
            prompt += f"\n{lock_block}\n"

        # v1.0.2: no first-pass word-count calibration instructions — the model has no internal
        # counter, so calibration instructions are only probabilistic suggestions.
        # Word-count control relies entirely on the auto-correction pipeline in the AI-modify
        # phase of write_chapter_with_control.

        system = _build_writing_system_prompt(
            self.report_type, 0, 0, writing_hint,
            chapter_title=chapter_title,
            topic=topic,
        )

        return prompt, system

    # ── Modification-execution (v1.0.2 §6.5, v1.0.4: tech analysis rules carried through) ──
    def modify_chapter(self, original_content: str, instruction: str,
                       chapter_budget: int = 0, auto_compress: bool = False,
                       chapter_title: str = "", topic: str = "") -> str:
        """Apply user modification instructions to chapter content locally.

        Word-count constraint (per feature spec):
        - If chapter_budget is provided -> stay within budget ±10%
        - If instruction mentions word count -> strictly follow it
        - Otherwise -> preserve original word count scale

        auto_compress=True: auto-compression mode. Temperature drops to 0.15, freq_penalty
        rises to 0.5, top_p drops to 0.8, to reduce hallucination and repetition.

        v1.0.4: tech analysis rules are carried through to prevent fabricated parameters
        during auto-compress/expand.
        """
        prompt, system = self._build_modify_args(
            original_content, instruction, chapter_budget,
            report_type=self.report_type,
            chapter_title=chapter_title,
            topic=topic,
        )
        if auto_compress:
            return self.llm.chat(prompt, system_prompt=system, temperature=0.15,
                                 frequency_penalty=0.5,
                                 presence_penalty=0.25,
                                 top_p=0.8)
        return self.llm.chat(prompt, system_prompt=system, temperature=TEMPERATURE_MODIFY,
                             frequency_penalty=FREQUENCY_PENALTY,
                             presence_penalty=PRESENCE_PENALTY,
                             top_p=TOP_P)

    def modify_chapter_stream(self, original_content: str, instruction: str,
                               callback=None, chapter_budget: int = 0,
                               auto_compress: bool = False,
                               chapter_title: str = "", topic: str = "") -> str:
        """Streaming version: apply modification instructions locally (with budget control)."""
        prompt, system = self._build_modify_args(
            original_content, instruction, chapter_budget,
            report_type=self.report_type,
            chapter_title=chapter_title,
            topic=topic,
        )
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        if auto_compress:
            return self.llm.chat_stream(messages, temperature=0.15,
                                        callback=callback,
                                        frequency_penalty=0.5,
                                        presence_penalty=0.25,
                                        top_p=0.8)
        return self.llm.chat_stream(messages, temperature=TEMPERATURE_MODIFY,
                                    callback=callback,
                                    frequency_penalty=FREQUENCY_PENALTY,
                                    presence_penalty=PRESENCE_PENALTY,
                                    top_p=TOP_P)

    # ── Modification helper: build Prompt / System ──
    def _build_modify_args(self, original_content: str, instruction: str,
                           chapter_budget: int,
                           report_type: str = "",
                           chapter_title: str = "",
                           topic: str = "") -> tuple:
        """Return (prompt, system).

        Shared by modify_chapter / modify_chapter_stream.
        v1.0.4: tech analysis rules are carried through to prevent fabricated parameters
        during auto-compress/expand.
        """
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

        # FRL-009: inject tech analysis rules when applicable to prevent re-introducing
        # fabricated parameters or unconditional recommendations during modification
        tech_rules = _build_tech_analysis_rules(report_type, chapter_title or "", topic or "")
        if tech_rules:
            system += "\n\n" + tech_rules

        prompt = (
            f"## 原文\n{original_content}\n\n"
            f"## 修改意见\n{instruction}\n\n"
            f"请根据上述修改意见，返回修改后的完整章节内容："
        )
        return prompt, system

    # ── Helper methods ──
    @staticmethod
    def _parse_chapter_seq(chapter_title: str) -> int:
        """Extract chapter seq from a '第X章 xxx' heading (e.g. '第二章 发展基础' -> 2)."""
        import re
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

    def _word_target(self, outline_md: str) -> tuple:
        """Return (total_words, chapter_count, per_chapter_target)."""
        total = self.total_words
        if total <= 0:
            return 0, 0, 0
        ch_count = _count_chapters(outline_md)
        return total, ch_count, total // ch_count

    def _build_prev_context(self, predecessor_chapters: dict) -> str:
        """Build the preceding-chapter body (full text; feature spec requires passing the full text of predecessor chapters)."""
        if not predecessor_chapters:
            return ""
        parts = []
        for num, content in predecessor_chapters.items():
            parts.append(f"## 第 {num} 章\n{content}")
        return "\n\n---\n\n".join(parts)

    # ── Cross-chapter plan lock (v1.0.2) ──
    def _build_cross_chapter_lock(self, outline_md: str,
                                  predecessor_chapters: dict) -> str:
        """Build the cross-chapter plan-lock constraint block.

        Scans outline_md, finds all sections containing multi-option comparison instructions.
        For completed comparison chapters among predecessors, generates lock statements so
        subsequent chapters do not re-compare.

        Returns: lock-constraint Markdown string; empty when there are no predecessor comparisons.
        """
        import re

        if not predecessor_chapters:
            return ""

        lines = outline_md.split('\n')
        ch_pattern = re.compile(r'^#\s+第([一二三四五六七八九十百零\d]+)章')

        # Extract chapter seq (compatible with Markdown heading lines)
        def _extract_ch_seq(line: str) -> int:
            m = ch_pattern.match(line)
            if not m:
                return 0
            return self._parse_chapter_seq(f"第{m.group(1)}章")

        comparison_points = {}  # {ch_num: [(section_title, instruction_text)]}
        seen_subtitles = set()   # Dedup: already processed comparison subtitles
        current_ch = 0
        current_section = ""

        for i, line in enumerate(lines):
            ch_m = ch_pattern.match(line)
            if ch_m:
                current_ch = _extract_ch_seq(line)
                continue

            if current_ch not in predecessor_chapters:
                continue

            # Track section-heading context
            if line.startswith('## '):
                current_section = line.strip('# ').strip()
            elif line.startswith('### '):
                current_section = line.strip('# ').strip()

            # Detect comparison instructions: prefer matching comparison-description lines with parentheses
            # Pattern A: heading line contains both "比选" and parenthesized description (e.g. ### 5.1.1 技术路线比选)
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

            # Pattern B: heading line contains "比选", followed by separate parenthesized description
            if line.startswith('###') and '比选' in line and '（' not in line:
                # Comparison heading -> look for parenthesized description in the following lines
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
                        break  # Reached the next heading, stop searching

        if not comparison_points:
            return ""

        locks = ["\n## 🔒 跨章方案锁定（全局约束）"]
        locks.append(
            "\n以下前序章节已完成多方案比选，各项推荐方案已经锁定。"
            "**本章所有内容必须在已锁定的推荐方案基础上展开，不得重新比较或引入新的备选方案：**\n"
        )

        for ch_num in sorted(comparison_points.keys()):
            # Retrieve chapter title
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
# Tech review result parser (v1.0.4)
# ═══════════════════════════════════════════════════════════════

_VALID_TECH_REVIEW_STATUSES = ("通过", "需补充", "不适用")


def parse_tech_review_result(raw_output: str) -> dict:
    """Parse and validate tech review LLM output.

    Returns a structured dict with:
      - status: one of "通过", "需补充", "不适用"
      - reason: explanation text
      - details: detailed findings
      - suggestions: improvement suggestions
      - data_gap_checklist: list of missing data items (required when status is "需补充")
      - parse_error: error message if parsing failed (None on success)

    On parse failure, returns a dict with parse_error set for retry handling.
    """
    import re

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

    # Extract status (look for Chinese status markers)
    status_match = re.search(r'(?:状态|校核结果|结论)[：:]\s*(通过|需补充|不适用)', text)
    if not status_match:
        # Try standalone status keywords
        for status in _VALID_TECH_REVIEW_STATUSES:
            if status in text[:200]:  # Status should appear early
                result["status"] = status
                break
    else:
        result["status"] = status_match.group(1)

    if result["status"] not in _VALID_TECH_REVIEW_STATUSES:
        result["parse_error"] = f"Unrecognized status: {result['status'] or 'missing'}"
        result["status"] = "不适用"
        return result

    # Extract reason
    reason_match = re.search(r'(?:原因|问题)[：:]\s*(.+?)(?:\n|$)', text)
    if reason_match:
        result["reason"] = reason_match.group(1).strip()

    # Extract details
    details_match = re.search(r'(?:详情|详细|发现)[：:]\s*(.+?)(?:\n\n|\n(?:建议|资料|清单)|$)', text, re.DOTALL)
    if details_match:
        result["details"] = details_match.group(1).strip()

    # Extract suggestions
    sugg_match = re.search(r'(?:建议|改进建议)[：:]\s*(.+?)(?:\n\n|\n(?:资料|清单|$)|$)', text, re.DOTALL)
    if sugg_match:
        result["suggestions"] = sugg_match.group(1).strip()

    # Extract data gap checklist for "需补充" status
    if result["status"] == "需补充":
        checklist_match = re.search(r'(?:资料清单|缺失资料|需补充资料)[：:]\s*(.+?)(?:\n\n|$)', text, re.DOTALL)
        if checklist_match:
            items_text = checklist_match.group(1).strip()
            # Parse list items (lines starting with - * or numbers)
            items = re.findall(r'[-*\d.]\s*(.+?)(?:\n|$)', items_text)
            result["data_gap_checklist"] = [item.strip() for item in items if item.strip()]
        if not result["data_gap_checklist"]:
            result["parse_error"] = "Status is '需补充' but no data gap checklist found"

    return result
