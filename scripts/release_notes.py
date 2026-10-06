"""
从 CHANGELOG.md 提取指定版本的段落，写入 release-notes.md（供 GitHub Release 使用）。

用法：python scripts/release_notes.py v1.6.3 [输出文件]
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def extract(version: str, changelog: str) -> str:
    ver = version.lstrip("v")
    pattern = rf"^##\s+v{re.escape(ver)}\b.*?(?=^##\s|\Z)"
    match = re.search(pattern, changelog, re.S | re.M)
    if match:
        return match.group(0).strip() + "\n"
    return f"Release v{ver}\n"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/release_notes.py <version> [out_file]")
        return 2
    version = sys.argv[1]
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO_ROOT / "release-notes.md"
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    body = extract(version, changelog)
    out_path.write_text(body, encoding="utf-8")
    print(f"release notes for {version} -> {out_path} ({len(body)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
