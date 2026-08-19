"""
FairyReport Backend — 认证端点（send-code / register / login / me）
"""
import secrets
from datetime import timedelta

import jwt as pyjwt
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import smtp
from ..config import settings
from ..db import get_db, utcnow
from ..models import AuthCode, User
from . import security
from .schemas import LoginRequest, RegisterRequest, SendCodeRequest, TokenResponse, UserResponse

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/users", tags=["users"])


@auth_router.post("/send-code")
def send_code(req: SendCodeRequest, db: Session = Depends(get_db)):
    """发送邮箱验证码：6 位数字码；60 秒重发间隔与每邮箱每日上限限频。"""
    now = utcnow()
    latest = db.execute(
        select(AuthCode)
        .where(AuthCode.email == req.email)
        .order_by(AuthCode.created_at.desc(), AuthCode.id.desc())
    ).scalars().first()
    if latest is not None and now - latest.created_at < timedelta(seconds=settings.auth_code_resend_interval_seconds):
        raise HTTPException(status_code=429, detail="发送过于频繁，请稍后再试")
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today = db.scalar(
        select(func.count())
        .select_from(AuthCode)
        .where(AuthCode.email == req.email, AuthCode.created_at >= day_start)
    )
    if sent_today >= settings.auth_code_daily_limit:
        raise HTTPException(status_code=429, detail="今日验证码发送次数已达上限")
    code = f"{secrets.randbelow(10**6):06d}"
    db.add(AuthCode(
        email=req.email,
        code=code,
        created_at=now,
        expires_at=now + timedelta(minutes=settings.auth_code_expire_minutes),
    ))
    db.commit()
    smtp.send_code_email(req.email, code)
    return {"message": "验证码已发送", "expires_seconds": settings.auth_code_expire_minutes * 60}


@auth_router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """注册新用户：校验验证码有效与邮箱唯一，密码加盐哈希存储。"""
    now = utcnow()
    record = db.execute(
        select(AuthCode)
        .where(AuthCode.email == req.email, AuthCode.code == req.code, AuthCode.expires_at > now)
        .order_by(AuthCode.created_at.desc(), AuthCode.id.desc())
    ).scalars().first()
    if record is None:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    exists = db.execute(select(User.id).where(User.email == req.email)).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="该邮箱已注册")
    password_hash, salt = security.hash_password(req.password)
    user = User(email=req.email, password_hash=password_hash, salt=salt)
    db.add(user)
    db.execute(delete(AuthCode).where(AuthCode.email == req.email))
    db.commit()
    return {"message": "注册成功", "email": user.email}


@auth_router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """邮箱+密码登录，返回 JWT；邮箱不存在或密码错误统一 401（避免用户枚举）。"""
    user = db.execute(select(User).where(User.email == req.email)).scalars().first()
    if user is None or not security.verify_password(req.password, user.salt, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    return TokenResponse(access_token=security.create_access_token(user.id, user.email))


def current_user(authorization: str | None, db: Session) -> User:
    """解析 Bearer JWT 并返回当前用户；缺失/无效/过期一律 401。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证凭据")
    token = authorization[len("Bearer "):].strip()
    try:
        payload = security.decode_access_token(token)
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=401, detail="认证凭据无效或已过期")
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="认证凭据无效")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


@users_router.get("/me", response_model=UserResponse)
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """依据有效 JWT 返回当前用户信息。"""
    user = current_user(authorization, db)
    return UserResponse(id=user.id, email=user.email, created_at=user.created_at)
