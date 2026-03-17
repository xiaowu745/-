"""用户系统 API"""

import hashlib
import hmac
import json
import base64
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import get_settings
from models.database import (
    get_db, UserRecord, AssessmentRecord, InterviewRecord,
)

router = APIRouter()
settings = get_settings()


class RegisterRequest(BaseModel):
    nickname: str
    phone: str = ""
    openid: str = ""  # 微信登录时使用


class LoginRequest(BaseModel):
    openid: str = ""
    phone: str = ""


class TokenResponse(BaseModel):
    access_token: str
    user_id: int
    nickname: str


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def create_token(user_id: int) -> str:
    """生成简易JWT Token (HS256)"""
    expire = int(time.time()) + settings.access_token_expire_minutes * 60
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64encode(json.dumps({"sub": str(user_id), "exp": expire}).encode())
    msg = f"{header}.{payload}"
    sig = hmac.new(settings.secret_key.encode(), msg.encode(), hashlib.sha256).digest()
    return f"{msg}.{_b64encode(sig)}"


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    """注册新用户"""
    db = get_db()
    try:
        # 检查openid是否已存在
        if req.openid:
            existing = db.query(UserRecord).filter_by(openid=req.openid).first()
            if existing:
                token = create_token(existing.id)
                return TokenResponse(
                    access_token=token,
                    user_id=existing.id,
                    nickname=existing.nickname,
                )

        user = UserRecord(
            nickname=req.nickname,
            phone=req.phone,
            openid=req.openid or None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_token(user.id)
        return TokenResponse(
            access_token=token,
            user_id=user.id,
            nickname=user.nickname,
        )
    finally:
        db.close()


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """登录（通过openid或手机号）"""
    db = get_db()
    try:
        user = None
        if req.openid:
            user = db.query(UserRecord).filter_by(openid=req.openid).first()
        elif req.phone:
            user = db.query(UserRecord).filter_by(phone=req.phone).first()

        if not user:
            raise HTTPException(status_code=404, detail="用户不存在，请先注册")

        user.last_active = datetime.now()
        db.commit()

        token = create_token(user.id)
        return TokenResponse(
            access_token=token,
            user_id=user.id,
            nickname=user.nickname,
        )
    finally:
        db.close()


@router.get("/profile/{user_id}")
async def get_profile(user_id: int):
    """获取用户信息及测评历史"""
    db = get_db()
    try:
        user = db.query(UserRecord).filter_by(id=user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 获取测评历史
        assessments = db.query(AssessmentRecord).filter_by(
            user_id=user_id
        ).order_by(AssessmentRecord.created_at.desc()).limit(10).all()

        # 获取面试记录
        interviews = db.query(InterviewRecord).filter_by(
            user_id=user_id
        ).order_by(InterviewRecord.created_at.desc()).limit(10).all()

        return {
            "user": {
                "id": user.id,
                "nickname": user.nickname,
                "created_at": str(user.created_at),
                "last_active": str(user.last_active),
            },
            "assessments": [
                {
                    "session_id": a.session_id,
                    "major": a.major,
                    "grade": a.grade,
                    "overall_score": a.overall_score,
                    "status": a.status,
                    "created_at": str(a.created_at),
                }
                for a in assessments
            ],
            "interviews": [
                {
                    "session_id": i.session_id,
                    "target_position": i.target_position,
                    "interview_type": i.interview_type,
                    "created_at": str(i.created_at),
                }
                for i in interviews
            ],
            "stats": {
                "total_assessments": len(assessments),
                "total_interviews": len(interviews),
                "best_score": max((a.overall_score or 0 for a in assessments), default=0),
            },
        }
    finally:
        db.close()


@router.get("/history/{user_id}/assessments")
async def get_assessment_history(user_id: int):
    """获取测评成长曲线数据"""
    db = get_db()
    try:
        assessments = db.query(AssessmentRecord).filter_by(
            user_id=user_id
        ).order_by(AssessmentRecord.created_at.asc()).all()

        return {
            "history": [
                {
                    "date": str(a.created_at.date()) if a.created_at else "",
                    "overall_score": a.overall_score,
                    "dimension_scores": a.dimension_scores,
                }
                for a in assessments
                if a.overall_score is not None
            ]
        }
    finally:
        db.close()
