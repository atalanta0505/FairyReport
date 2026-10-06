"""
一条命令发布说明：算 SHA256 → 更新 GitHub 与 Gitee 的 Release 说明 → 附上校验文件。

用法：
    python scripts/publish_notes.py v1.6.5 --netdisk "https://pan.baidu.com/s/xxxx?pwd=abcd" --netdisk-code abcd

可选参数：
    --zip PATH        指定便携包路径（默认 dist/FairyReport-Local-v<版本>-Windows-x64.zip）
    --gitee-token-file PATH   Gitee 私人令牌文件（默认 %USERPROFILE%\\..\\Personal 下的约定路径，可用环境变量 GITEE_TOKEN 覆盖）
    --no-github / --no-gitee  跳过对应平台
    --upload-zip      顺带把便携包也上传到 GitHub Release（默认只传校验文件）

约定：版本号唯一来源 desktop/package.json；说明正体取自 CHANGELOG.md 对应版本段落。
令牌只从文件或环境变量读取，绝不打印。
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OWNER = "atalanta0505"
GITEE_REPO = "fairy-report_lite"
GITHUB_REPO = "FairyReport"
DEFAULT_TOKEN_FILE = Path(r"D:\\Personal\\gitee_opencode_private_access.txt")
GITEE_API = "https://gitee.com/api/v5"


def package_version() -> str:
    with open(REPO_ROOT / "desktop" / "package.json", encoding="utf-8") as fh:
        return json.load(fh)["version"]


def changelog_entry(version: str) -> str:
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(rf"^##\s+v{re.escape(version)}\b.*?(?=^##\s|\Z)", text, re.S | re.M)
    if not match:
        print(f"警告：CHANGELOG.md 中没有 v{version} 段落，说明将只包含下载信息。")
        return f"## v{version}"
    return match.group(0).strip()


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def build_body(version: str, zip_name: str, sha: str, netdisk: str, netdisk_code: str) -> str:
    parts = ["## 下载", ""]
    if netdisk:
        parts.append("**国内（网盘，推荐）**")
        line = f"链接：{netdisk}"
        if netdisk_code:
            line += f"　提取码：`{netdisk_code}`"
        parts += [line, ""]
    parts += [
        "**GitHub（备用）**",
        f"https://github.com/{OWNER}/{GITHUB_REPO}/releases/tag/v{version}",
        "",
        "**校验值（SHA256）**",
        "```",
        f"{sha}  {zip_name}",
        "```",
        f"下载后可在 PowerShell 里核对：`Get-FileHash .\\{zip_name} -Algorithm SHA256`",
        "",
        "---",
        "",
        changelog_entry(version),
        "",
    ]
    return "\n".join(parts)


def update_github(tag: str, notes_file: Path, checksum_file: Path, zip_path: Path, upload_zip: bool) -> None:
    def run(*args):
        result = subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout).strip()[:300])
        return (result.stdout or "").strip()

    run("gh", "release", "edit", tag, "--notes-file", str(notes_file))
    print(f"  GitHub：{tag} 说明已更新")
    files = [str(checksum_file)] + ([str(zip_path)] if upload_zip else [])
    run("gh", "release", "upload", tag, *files, "--clobber")
    print("  GitHub：附件已更新（" + "、".join(Path(f).name for f in files) + "）")


def gitee_request(method: str, path: str, token: str, payload=None):
    url = f"{GITEE_API}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    body = dict(payload or {})
    body["access_token"] = token
    if method in ("POST", "PATCH", "PUT"):
        data = json.dumps(body).encode("utf-8")
    else:
        url += ("&" if "?" in url else "?") + "access_token=" + urllib.parse.quote(token)
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8") or "null")


def gitee_upload_attachment(release_id: int, token: str, file_path: Path) -> bool:
    boundary = "----frl" + uuid.uuid4().hex
    chunks = []
    for name, value in (("access_token", token),):
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode("utf-8"))
    chunks.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{file_path.name}\"\r\n"
        f"Content-Type: application/octet-stream\r\n\r\n".encode("utf-8")
    )
    chunks.append(file_path.read_bytes())
    chunks.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(chunks)
    request = urllib.request.Request(
        f"{GITEE_API}/repos/{OWNER}/{GITEE_REPO}/releases/{release_id}/attach_files",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:  # noqa: BLE001
        print(f"  Gitee：校验文件上传失败（{exc}），说明已更新，可忽略")
        return False


def update_gitee(tag: str, version: str, body: str, token: str, checksum_file: Path) -> None:
    existing = gitee_request("GET", f"/repos/{OWNER}/{GITEE_REPO}/releases/tags/{tag}", token)
    if existing:
        release_id = existing["id"]
        # Gitee 的 PATCH 必须带上 tag_name，否则返回 400 tag_name is missing
        gitee_request("PATCH", f"/repos/{OWNER}/{GITEE_REPO}/releases/{release_id}", token,
                      {"tag_name": tag, "name": f"FairyReport v{version}", "body": body, "prerelease": False})
        print(f"  Gitee：{tag} 说明已更新（id={release_id}）")
    else:
        created = gitee_request("POST", f"/repos/{OWNER}/{GITEE_REPO}/releases", token,
                                {"tag_name": tag, "name": f"FairyReport v{version}",
                                 "body": body, "target_commitish": "master", "prerelease": False})
        release_id = created["id"]
        print(f"  Gitee：{tag} 发行版已创建（id={release_id}）")
    gitee_upload_attachment(release_id, token, checksum_file)


def main() -> int:
    parser = argparse.ArgumentParser(description="发布 GitHub/Gitee 的版本说明与校验文件")
    parser.add_argument("version", help="版本号，如 v1.6.5 或 1.6.5")
    parser.add_argument("--netdisk", default="", help="网盘分享链接（可含提取码）")
    parser.add_argument("--netdisk-code", default="", help="网盘提取码")
    parser.add_argument("--zip", dest="zip_path", default="", help="便携包路径")
    parser.add_argument("--gitee-token-file", default=str(DEFAULT_TOKEN_FILE))
    parser.add_argument("--no-github", action="store_true")
    parser.add_argument("--no-gitee", action="store_true")
    parser.add_argument("--upload-zip", action="store_true", help="同时上传便携包到 GitHub Release")
    args = parser.parse_args()

    version = args.version.lstrip("v")
    tag = f"v{version}"
    current = package_version()
    if version != current:
        print(f"注意：命令里的版本 v{version} 与 desktop/package.json 的 v{current} 不一致，按 v{version} 继续。")

    zip_path = Path(args.zip_path) if args.zip_path else REPO_ROOT / "dist" / f"FairyReport-Local-v{version}-Windows-x64.zip"
    if not zip_path.exists():
        print(f"错误：找不到便携包 {zip_path}")
        return 2
    sha = sha256_of(zip_path)
    checksum_file = REPO_ROOT / "dist" / "SHA256SUMS.txt"
    checksum_file.write_text(f"{sha}  {zip_path.name}\n", encoding="utf-8")
    print(f"便携包：{zip_path.name}（{zip_path.stat().st_size / 1048576:.1f} MB）")
    print(f"SHA256：{sha}")

    body = build_body(version, zip_path.name, sha, args.netdisk, args.netdisk_code)
    notes_file = REPO_ROOT / "release-notes.md"
    notes_file.write_text(body, encoding="utf-8")

    if not args.no_github:
        try:
            update_github(tag, notes_file, checksum_file, zip_path, args.upload_zip)
        except Exception as exc:  # noqa: BLE001
            print(f"  GitHub：更新失败（{exc}）")

    if not args.no_gitee:
        token = os.environ.get("GITEE_TOKEN", "").strip()
        if not token:
            token_path = Path(args.gitee_token_file)
            if token_path.exists():
                token = token_path.read_text(encoding="utf-8").strip()
        if not token:
            print("  Gitee：未找到令牌（--gitee-token-file 或 GITEE_TOKEN），已跳过")
        else:
            try:
                update_gitee(tag, version, body, token, checksum_file)
            except Exception as exc:  # noqa: BLE001
                print(f"  Gitee：更新失败（{exc}）")

    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
