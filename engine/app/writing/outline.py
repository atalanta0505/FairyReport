"""
大纲生成 — 移植自根目录 outline.py。

模板函数改调 engine writing.templates_loader（从已安装通用包读）。
"""
import re

from . import templates_loader as tmpl
from .prompts import (
    ORDER_SYSTEM_PROMPT,
    TEMPERATURE_HINT,
    TEMPERATURE_ORDER,
    TEMPERATURE_OUTLINE,
    _OUTLINE_BASE_PROMPT,
)


def _suggest_chapter_count(total_words: int) -> int:
    """根据全篇字数建议章节数。"""
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
    chapter_template = tmpl.get_chapter_template_prompt(report_type)
    if chapter_template:
        base += "\n" + chapter_template
    word_hint = ""
    if total_words > 0:
        if chapter_template:
            word_hint = f"\n**全篇目标字数：约{total_words:,}字**。请据此控制各节的详略深度，确保全篇不超目标字数。"
        else:
            ch_count = _suggest_chapter_count(total_words)
            word_hint = f"\n**全篇目标字数：约{total_words:,}字**。请据此控制大纲的章节数量（建议{ch_count}章左右）和各节深度，确保后续编写时每章节篇幅合理、全篇不超目标字数。"
    base += f"""{word_hint}"""
    template_notes = tmpl.get_template_notes(report_type)
    if template_notes:
        base += f"\n\n**模板规范**：{template_notes}"
    base += """
要求：
0. 禁止开场白：不要输出确认语或自我介绍，直接输出大纲内容。
1. 深度要求（极重要）：大纲必须全面细化下钻至三级（###）或四级（####）末级实施小节，每个二级节（##）下必须细分 2~5 个具体的末级小节，构建全书完整的标题骨架，严禁输出只有一级章或二级节的粗粒度空章。
2. 大纲要覆盖当前报告类型的完整专业结构与标准规范
3. 所有级别的标题都必须带编号：
   - 一级（#）：`# 第一章 xxx`
   - 二级（##）：`## 1.1 xxx`
   - 三级（###）：`### 1.1.1 xxx`
   - 四级（####）：`#### 1.1.1.1 xxx`
   - 五级（#####）：`##### 1.1.1.1.1 xxx`
4. 标题只写简明主题词，禁止添加括号描述。
5. 标题标记（#）只用于结构性标题，不要对描述性、阐释性文字使用 # 格式。
6. 返回纯 Markdown，不要包含 JSON 或代码块标记。
"""
    return base


class OutlineGenerator:
    def __init__(self, llm, report_type: str = "", total_words: int = 0):
        self.llm = llm
        self.report_type = report_type
        self.total_words = total_words

    def generate(self, report_name: str = "", context: str = "") -> str:
        # 模板即大纲：优先用模板预定义 outline_md，跳过 LLM
        template_outline = tmpl.get_template_outline_md(self.report_type)
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
        """流式大纲生成。callback(chunk_text) 每块回调。"""
        template_outline = tmpl.get_template_outline_md(self.report_type)
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
        """返回 (order_list, reason_str) — order_list 如 [2,3,4,1,5]。"""
        prompt = (
            f"已生成以下大纲：\n\n{outline_md}\n\n"
            f"请按从上到下的顺序为每个「第X章」编号（1,2,3...），"
            f"然后建议一个最优写作顺序。\n"
            f"只返回逗号分隔的数字序列，如 2,3,4,1,5"
        )
        raw = self.llm.chat(prompt, system_prompt=ORDER_SYSTEM_PROMPT, temperature=TEMPERATURE_ORDER).strip()

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
        """从大纲 MD + 写作顺序构建 outline.json 结构。"""
        if chapter_titles is None:
            chapter_titles = _extract_chapter_titles(outline_md)

        order_map = {}
        for rank_i, num in enumerate(writing_order):
            order_map[num] = rank_i + 1

        chapters = []
        for seq in sorted(chapter_titles.keys(), key=lambda x: int(x)):
            chapters.append({
                "chapter_seq": seq,
                "title": chapter_titles[seq],
                "writing_hint": "",
                "writing_order": order_map.get(seq, 0),
                "word_budget": tmpl.get_chapter_word_budget(report_type, seq) if report_type else 0,
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
        if not outline_json or "chapters" not in outline_json:
            return
        for ch in outline_json["chapters"]:
            if ch.get("chapter_seq") == chapter_seq:
                ch["writing_hint"] = hint
                break

    @staticmethod
    def get_hint(outline_json: dict, chapter_seq: int) -> str:
        if not outline_json or "chapters" not in outline_json:
            return ""
        for ch in outline_json["chapters"]:
            if ch.get("chapter_seq") == chapter_seq:
                return ch.get("writing_hint", "")
        return ""

    @staticmethod
    def update_outline_json_title(outline_json: dict, chapter_seq: int, new_title: str):
        if not outline_json or "chapters" not in outline_json:
            return
        for ch in outline_json["chapters"]:
            if ch.get("chapter_seq") == chapter_seq:
                ch["title"] = new_title
                break


def _extract_chapter_titles(outline_md: str) -> dict:
    """从大纲 Markdown 提取章标题，返回 {num: title}。"""
    titles = re.findall(
        r'^#{1,2}\s+(第[一二三四五六七八九十百零\d]+章[\s：:].+)$',
        outline_md, re.MULTILINE
    )
    if not titles:
        titles = re.findall(
            r'^#{1,2}\s+(第[一二三四五六七八九十百零\d]+章.+)$',
            outline_md, re.MULTILINE
        )
    if not titles:
        titles = re.findall(
            r'^(第[一二三四五六七八九十百零\d]+章[\s：:].+)$',
            outline_md, re.MULTILINE
        )
    return {i + 1: t.strip() for i, t in enumerate(titles)}


def parse_chapter_seq(chapter_title: str) -> int:
    """从 '第X章 xxx' 标题提取章序号（阿拉伯数字）。"""
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
    if '十' in num_str:
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
