"""数据库模型与连接管理

MVP阶段支持两种模式：
1. SQLite（默认，无需额外配置）
2. PostgreSQL（生产环境）
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    create_engine, Column, String, Integer, Text, DateTime, JSON, Float,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config import get_settings

settings = get_settings()

# MVP默认用SQLite，零配置启动
if "postgresql" in settings.database_url:
    SQLALCHEMY_URL = settings.database_url.replace("+asyncpg", "")
else:
    # 直接使用环境变量中的配置，支持相对/绝对路径
    SQLALCHEMY_URL = settings.database_url or "sqlite:///./skill_agent.db"

engine = create_engine(
    SQLALCHEMY_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_URL else {},
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ============ 数据表定义 ============

class UserRecord(Base):
    """用户记录"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    openid = Column(String(128), unique=True, index=True, nullable=True)  # 微信openid
    nickname = Column(String(50))
    phone = Column(String(20), nullable=True)
    wechat = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    last_active = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AssessmentRecord(Base):
    """测评记录"""
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(32), unique=True, index=True)
    user_id = Column(Integer, nullable=True)

    # 学生信息
    nickname = Column(String(50))
    major = Column(String(50))
    grade = Column(String(20))
    school_tier = Column(String(20))
    phone = Column(String(20), nullable=True)
    wechat = Column(String(50), nullable=True)

    # 快速自评结果
    quick_answers = Column(JSON, nullable=True)      # 原始答案
    dimension_scores = Column(JSON, nullable=True)    # 各维度得分
    overall_score = Column(Integer, nullable=True)
    weak_dimensions = Column(JSON, nullable=True)

    # 深度评估结果
    deep_result = Column(JSON, nullable=True)
    chat_history = Column(JSON, nullable=True)        # 对话历史

    # 推荐方向
    recommended_directions = Column(JSON, nullable=True)

    # 报告
    report_text = Column(Text, nullable=True)

    # 状态
    status = Column(String(20), default="quick_done")  # quick_done / deep_in_progress / deep_done / report_generated

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class InterviewRecord(Base):
    """面试模拟记录"""
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(32), unique=True, index=True)
    assessment_session_id = Column(String(32), nullable=True)
    user_id = Column(Integer, nullable=True)

    target_position = Column(String(50))
    interview_type = Column(String(20))  # technical / hr / project
    chat_history = Column(JSON, nullable=True)
    feedback = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.now)


class ChatRecord(Base):
    """自由问答记录"""
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(32), index=True)
    user_id = Column(Integer, nullable=True)
    role = Column(String(10))  # user / assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


# ============ 数据库操作 ============

def init_db():
    """初始化数据库（创建表）

    捕获 "table already exists" 异常，避免多 worker 并发初始化时报错。
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        if "already exists" not in str(e):
            raise


def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def save_assessment(session_id: str, data: dict):
    """保存或更新测评记录"""
    db = get_db()
    try:
        record = db.query(AssessmentRecord).filter_by(session_id=session_id).first()
        if not record:
            record = AssessmentRecord(session_id=session_id)
            db.add(record)

        student = data.get("student", {})
        record.nickname = student.get("nickname", "")
        record.major = student.get("major", "")
        record.grade = student.get("grade", "")
        record.school_tier = student.get("school_tier", "")

        if "quick_answers" in data:
            record.quick_answers = data["quick_answers"]
        if "dimension_scores" in data:
            record.dimension_scores = data["dimension_scores"]
        if "overall_score" in data:
            record.overall_score = data["overall_score"]
        if "weak_dimensions" in data:
            record.weak_dimensions = data["weak_dimensions"]
        if "deep_result" in data:
            record.deep_result = data["deep_result"]
        if "chat_history" in data:
            record.chat_history = data["chat_history"]
        if "recommended_directions" in data:
            record.recommended_directions = data["recommended_directions"]
        if "report_text" in data:
            record.report_text = data["report_text"]
        if "status" in data:
            record.status = data["status"]
        if "phone" in data:
            record.phone = data["phone"]
        if "wechat" in data:
            record.wechat = data["wechat"]

        record.updated_at = datetime.now()
        db.commit()
    finally:
        db.close()


def get_assessment(session_id: str) -> Optional[dict]:
    """获取测评记录"""
    db = get_db()
    try:
        record = db.query(AssessmentRecord).filter_by(session_id=session_id).first()
        if not record:
            return None
        return {
            "session_id": record.session_id,
            "nickname": record.nickname,
            "major": record.major,
            "grade": record.grade,
            "overall_score": record.overall_score,
            "dimension_scores": record.dimension_scores,
            "status": record.status,
            "created_at": str(record.created_at),
        }
    finally:
        db.close()


def get_user_assessments(user_id: int) -> list[dict]:
    """获取用户的所有测评记录"""
    db = get_db()
    try:
        records = db.query(AssessmentRecord).filter_by(user_id=user_id).order_by(
            AssessmentRecord.created_at.desc()
        ).all()
        return [
            {
                "session_id": r.session_id,
                "major": r.major,
                "overall_score": r.overall_score,
                "status": r.status,
                "created_at": str(r.created_at),
            }
            for r in records
        ]
    finally:
        db.close()
