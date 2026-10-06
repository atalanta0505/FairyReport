"""
校验两份指南与当前版本同步：不得残留旧版本号，且必须标注当前版本。

用法：python scripts/check_guides.py（不一致时退出码 1）
版本号唯一来源：desktop/package.json
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUIDES = ("docs/USER_GUIDE.md", "docs/BEGINNER_GUIDE.md")


def main() -> int:
    version = json.loads((REPO_ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))["version"]
    problems = []
    for rel in GUIDES:
        path = REPO_ROOT / rel
        if not path.exists():
            problems.append(f"{rel}：文件不存在")
            continue
        text = path.read_text(encoding="utf-8")
        found = sorted(set(re.findall(r"v(\d+\.\d+\.\d+)", text)))
        stale = [v for v in found if v != version]
        if stale:
            problems.append(f"{rel}：仍引用旧版本 " + "、".join("v" + v for v in stale) + f"（当前 v{version}）")
        if f"v{version}" not in text:
            problems.append(f"{rel}：未标注当前版本 v{version}")

    if problems:
        print(f"指南与当前版本（v{version}）不同步：")
        for item in problems:
            print("  - " + item)
        print("请更新 docs/USER_GUIDE.md 与 docs/BEGINNER_GUIDE.md 后重试。")
        return 1

    print(f"指南版本校验通过：两份指南均为 v{version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
