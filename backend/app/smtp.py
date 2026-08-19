"""
FairyReport Backend — QQ SMTP 发信封装（stdlib smtplib，后台线程执行）

凭据只从 settings（环境变量 / backend/.env）读取，禁止硬编码。
"""
import smtplib
import ssl
import threading
from email.message import EmailMessage

from .config import settings


def build_code_message(to_addr: str, code: str) -> EmailMessage:
    """构造验证码邮件消息。"""
    msg = EmailMessage()
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_user}>"
    msg["To"] = to_addr
    msg["Subject"] = f"{settings.smtp_from_name} 邮箱验证码"
    msg.set_content(
        f"您的验证码为：{code}，{settings.auth_code_expire_minutes} 分钟内有效。\n"
        "如非本人操作，请忽略本邮件。请勿将验证码告知他人。"
    )
    return msg


def deliver(msg: EmailMessage) -> None:
    """通过 QQ SMTP（SSL）实际发送邮件；凭据缺失或发送失败时抛出异常。"""
    if not settings.smtp_user or not settings.smtp_auth_code:
        raise RuntimeError("SMTP 凭据未配置（SMTP_USER / SMTP_AUTH_CODE）")
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ssl.create_default_context()) as server:
        server.login(settings.smtp_user, settings.smtp_auth_code)
        server.send_message(msg)


def _deliver_quietly(msg: EmailMessage) -> None:
    """线程入口：捕获异常并打日志，避免后台线程静默失败无痕迹。"""
    try:
        deliver(msg)
    except Exception as exc:
        print(f"[smtp] 验证码邮件发送失败: {exc}")


def send_code_email(to_addr: str, code: str) -> None:
    """异步发送验证码邮件：后台守护线程执行实际发送，不阻塞请求。"""
    msg = build_code_message(to_addr, code)
    threading.Thread(target=_deliver_quietly, args=(msg,), daemon=True).start()
