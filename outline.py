"""
Outline — Outline generation, writing order suggestion, and writing hint generation (v1.0.5)
- Outline generation does not include writing_hint (auto-generated in the writing phase)
- outline.json schema includes a writing_order field for each chapter
"""
import re
from config import (
    get_word_limit,
    TEMPERATURE_OUTLINE, TEMPERATURE_ORDER, TEMPERATURE_HINT,
    get_template_notes, get_template_outline_md,
)

_OUTLINE_BASE_PROMPT = """\
你是资深工程咨询报告编制专家。
根据用户输入的项目主题、报告类型和参考资料片段，生成详细的报告大纲（Markdown 格式）。"""


def _suggest_chapter_count(total_words: int) -> int:
    """Suggest the number of outline chapters based on total word count."""
    if total_words >= 80000:
        return 18
    elif total_words >= 55000:
        return 14
    elif total_words >= 45000:
        return 12
    elif total_words >= 35000:
        return 10
    elif total_words >= 25000:
        return 7
    else:
        return 5


def _build_outline_system_prompt(report_type: str = "", total_words: int = 0) -> str:
    base = _OUTLINE_BASE_PROMPT
    if report_type:
        base += f"\n\n当前报告类型：**{report_type}**，请严格按照该类型的标准结构和章节规范生成大纲。"
    # Inject template chapter structure (for all report types with a template)
    from config import get_chapter_template_prompt as _get_chapter_template_prompt
    chapter_template = _get_chapter_template_prompt(report_type)
    if chapter_template:
        base += "\n" + chapter_template
    # Word constraint (when a fixed chapter template is present, only report the word count, do not suggest a chapter count)
    word_hint = ""
    if total_words > 0:
        if chapter_template:
            word_hint = f"\n**全篇目标字数：约{total_words:,}字**。请据此控制各节的详略深度，确保全篇不超目标字数。"
        else:
            ch_count = _suggest_chapter_count(total_words)
            word_hint = f"\n**全篇目标字数：约{total_words:,}字**。请据此控制大纲的章节数量（建议{ch_count}章左右）和各节深度，确保后续编写时每章节篇幅合理、全篇不超目标字数。"
    base += f"""{word_hint}"""
    # Inject template conventions (only when the template exists and has notes)
    template_notes = get_template_notes(report_type)
    if template_notes:
        base += f"\n\n**模板规范**：{template_notes}"
    base += """
要求：
0. 禁止开场白：不要输出确认语或自我介绍，直接输出大纲内容。
1. 标题深度可达 5 级（# ## ### #### #####），但非每章必达 5 级
2. 大纲要覆盖当前报告类型的完整结构
3. **所有级别的标题都必须带编号**：
   - 一级（#）：`# 第一章 xxx`
   - 二级（##）：`## 1.1 xxx`
   - 三级（###）：`### 1.1.1 xxx`
   - 四级（####）：`#### 1.1.1.1 xxx`
   - 五级（#####）：`##### 1.1.1.1.1 xxx`
4. **标题只写简明主题词，禁止添加括号描述**：标题中不要出现「（xxx）」之类的解释性文字。章节要点、涵盖范围等描述性内容属于正文，不应放入标题。
5. **标题标记（#）只用于结构性标题**，不要对描述性、阐释性文字使用 # 格式。非标题内容用普通段落表达。
6. 返回纯 Markdown，不要包含 JSON 或代码块标记
"""
    return base


ORDER_SYSTEM_PROMPT = """\
你是报告写作规划专家。分析大纲章节内容，建议最优写作顺序。
核心章节先写，总则和结论最后写。
先返回一行逗号分隔的章节序号（如 2,3,4,1,5），然后另起一行用 REASON: xxx 简短说明排序理由。"""


class OutlineGenerator:
    def __init__(self, llm, report_type: str = "", total_words: int = 0):
        self.llm = llm
        self.report_type = report_type
        self.total_words = total_words

    def generate(self, report_name: str = "", context: str = "") -> str:
        # ── Template is the outline: prefer the template's predefined outline_md, skip the LLM ──
        template_outline = get_template_outline_md(self.report_type)
        if template_outline:
            return template_outline

        system = _build_outline_system_prompt(self.report_type, self.total_words)
        report_label = f" [{self.report_type}]" if self.report_type else ""
        prompt = (
            f"请为以下项目生成详细的报告大纲{report_label}：\n\n"
            f"**项目名称**：{report_name}\n\n"
            f"**参考资料摘要**：\n{context}\n\n"
            f"请生成详细的 Markdown 大纲（使用 # 到 ##### 的标题层级）："
        )
        return self.llm.chat(prompt, system_prompt=system, temperature=TEMPERATURE_OUTLINE)

    def generate_stream(self, report_name: str = "", context: str = "", callback=None) -> str:
        """Streaming outline generation. callback(chunk_text) is invoked per chunk for real-time UI updates."""

        # Template is the outline: prefer the template's predefined outline_md, skip the LLM
        template_outline = get_template_outline_md(self.report_type)
        if template_outline:
            import time
            text = template_outline
            for i in range(0, len(text), 10):
                chunk = text[i:i + 10]
                if callback:
                    callback(chunk)
                time.sleep(0.005)
            return text

        system = _build_outline_system_prompt(self.report_type, self.total_words)
        report_label = f" [{self.report_type}]" if self.report_type else ""
        prompt = (
            f"请为以下项目生成详细的报告大纲{report_label}：\n\n"
            f"**项目名称**：{report_name}\n\n"
            f"**参考资料摘要**：\n{context}\n\n"
            f"请生成详细的 Markdown 大纲（使用 # 到 ##### 的标题层级）："
        )
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        return self.llm.chat_stream(messages, temperature=TEMPERATURE_OUTLINE, callback=callback)

    def suggest_order(self, outline_md: str) -> tuple:
        """Return (order_list, reason_string) — order_list e.g. [2,3,4,1,5]"""
        prompt = (
            f"已生成以下大纲：\n\n{outline_md}\n\n"
            f"请按从上到下的顺序为每个「第X章」编号（1,2,3...），"
            f"然后建议一个最优写作顺序。\n"
            f"只返回逗号分隔的数字序列，如 2,3,4,1,5"
        )
        raw = self.llm.chat(prompt, system_prompt=ORDER_SYSTEM_PROMPT, temperature=TEMPERATURE_ORDER).strip()

        # Parse: ORDER/REASON format or plain numeric line
        order_line = ""
        reason_line = ""
        for line in raw.split("\n"):
            line_stripped = line.strip()
            if line_stripped.upper().startswith("ORDER"):
                order_line = line_stripped
            elif line_stripped.upper().startswith("REASON"):
                reason_line = line_stripped
            elif re.match(r'^[\d,\s]+$', line_stripped) and not order_line:
                order_line = line_stripped

        if not order_line:
            order_line = raw

        numbers = re.findall(r'\d+', order_line)
        order = [int(n) for n in numbers] if numbers else []

        if ":" in reason_line:
            reason = reason_line.split(":", 1)[1].strip()
        else:
            reason = ""

        return order, reason

    @staticmethod
    def build_outline_json(outline_md: str, writing_order: list,
                           writing_order_reason: str = "",
                           chapter_titles: dict = None,
                           report_type: str = "") -> dict:
        """Build current outline.json structure from outline MD and writing order.

        Current schema:
        {
          "report_name": "...",
          "report_type": "...",
          "chapters": [
            {
              "chapter_seq": 1,
              "title": "第一章 总则",
              "writing_hint": "",        // initialize as empty
              "writing_order": 5,
              "word_budget": 3000,       // read from template JSON
              "notes": ""
            },
            ...
          ],
          "writing_order": [...],
          "writing_order_reason": "...",
          "current_order_idx": 0
        }

        Args:
            outline_md: outline Markdown
            writing_order: LLM-suggested writing order list
            writing_order_reason: LLM explanation of ordering logic
            chapter_titles: {num: title} dict (optional, auto-extracted from outline_md)
            report_type: report type, used to look up word_budget in the template

        Returns:
            dict: structured outline
        """
        # Extract chapter titles
        if chapter_titles is None:
            chapter_titles = _extract_chapter_titles(outline_md)

        # Build writing_order rank map: chapter_seq -> position+1 in writing_order
        order_map = {}
        for rank_i, num in enumerate(writing_order):
            order_map[num] = rank_i + 1

        # Look up per-chapter word budget
        from config import get_chapter_word_budget as _get_budget
        chapters = []
        for seq in sorted(chapter_titles.keys(), key=lambda x: int(x)):
            chapters.append({
                "chapter_seq": seq,
                "title": chapter_titles[seq],
                "writing_hint": "",         # initialize as empty
                "writing_order": order_map.get(seq, 0),
                "word_budget": _get_budget(report_type, seq) if report_type else 0,
                "notes": "",
            })

        return {
            "report_name": "",
            "report_type": "",
            "chapters": chapters,
            "writing_order": writing_order,
            "writing_order_reason": writing_order_reason,
            "current_order_idx": 0,
        }

    @staticmethod
    def update_outline_json_hint(outline_json: dict, chapter_seq: int, hint: str):
        """Write the given chapter's writing_hint back to outline_json."""
        if not outline_json or "chapters" not in outline_json:
            return
        for ch in outline_json["chapters"]:
            if ch.get("chapter_seq") == chapter_seq:
                ch["writing_hint"] = hint
                break

    @staticmethod
    def get_hint(outline_json: dict, chapter_seq: int) -> str:
        """Read the given chapter's writing_hint from outline_json."""
        if not outline_json or "chapters" not in outline_json:
            return ""
        for ch in outline_json["chapters"]:
            if ch.get("chapter_seq") == chapter_seq:
                return ch.get("writing_hint", "")
        return ""

    @staticmethod
    def update_outline_json_title(outline_json: dict, chapter_seq: int, new_title: str):
        """Update a chapter's title."""
        if not outline_json or "chapters" not in outline_json:
            return
        for ch in outline_json["chapters"]:
            if ch.get("chapter_seq") == chapter_seq:
                ch["title"] = new_title
                break


def _extract_chapter_titles(outline_md: str) -> dict:
    """Extract chapter titles from outline Markdown, return {num: title}."""
    # Prefer matching Markdown headings with #
    titles = re.findall(
        r'^#{1,2}\s+(第[一二三四五六七八九十百零\d]+章[\s：:].+)$',
        outline_md, re.MULTILINE
    )
    if not titles:
        titles = re.findall(
            r'^#{1,2}\s+(第[一二三四五六七八九十百零\d]+章.+)$',
            outline_md, re.MULTILINE
        )
    # Fallback: try matching even without # (to handle non-conforming LLM output)
    if not titles:
        titles = re.findall(
            r'^(第[一二三四五六七八九十百零\d]+章[\s：:].+)$',
            outline_md, re.MULTILINE
        )
    return {i + 1: t.strip() for i, t in enumerate(titles)}


def parse_chapter_seq(chapter_title: str) -> int:
    """Extract the chapter natural number (Arabic) from a '第X章 xxx' title."""
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
    # Chinese numeral conversion
    result = 0
    if '十' in num_str:
        # "十X": 10 + X (十一=11)
        # "X十": X * 10 (二十=20)
        # "X十Y": X * 10 + Y (二十五=25)
        parts = num_str.split('十')
        if num_str.startswith('十'):
            result = 10 + (cn_num_map.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0)
        else:
            result = cn_num_map.get(parts[0], 0) * 10
            if len(parts) > 1 and parts[1]:
                result += cn_num_map.get(parts[1], 0)
    else:
        for ch in num_str:
            result += cn_num_map.get(ch, 0)
    return result if result > 0 else 0
