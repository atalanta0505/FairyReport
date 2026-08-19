"""
FairyReport Backend — 认证 API 请求/响应模型
"""
import re
from datetime import datetime

from pydantic import BaseModel, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _check_email(value: str) -> str:
    """邮箱基础格式校验（不引入额外依赖）。"""
    value = value.strip().lower()
    if len(value) > 255 or not _EMAIL_RE.match(value):
        raise ValueError("邮箱格式不正确")
    return value


class SendCodeRequest(BaseModel):
    """send-code 请求体。"""

    email: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        return _check_email(v)


class RegisterRequest(BaseModel):
    """register 请求体。"""

    email: str
    code: str
    password: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        return _check_email(v)

    @field_validator("code")
    @classmethod
    def _validate_code(cls, v: str) -> str:
        if not re.fullmatch(r"\d{6}", v):
            raise ValueError("验证码须为 6 位数字")
        return v

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        if not 8 <= len(v) <= 64:
            raise ValueError("密码长度须为 8-64 位")
        return v


class LoginRequest(BaseModel):
    """login 请求体。"""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        return _check_email(v)


class TokenResponse(BaseModel):
    """login 成功响应。"""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """/api/users/me 响应。"""

    id: int
    email: str
    created_at: datetime
