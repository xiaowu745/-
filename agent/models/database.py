"""数据库模型与连接管理

MVP阶段支持两种模式：
1. SQLite（默认，无需额外配置）
2. PostgreSQL（生产环境）
"""

import json
from datetime import datetime

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


class Lead(Base):
    """私域线索（用户留资记录）

    用户在看报告前被弹窗拦截，填入手机号并勾选同意后保存一条 Lead。
    同一手机号 + 同一 session_id 视为同一条线索，会被 upsert。
    """
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), index=True)
    session_id = Column(String(32), index=True, nullable=True)

    # 冗余存储测评时填写的学生信息，方便后台直接查看和筛选
    nickname = Column(String(50), nullable=True)
    major = Column(String(50), nullable=True)
    grade = Column(String(20), nullable=True)
    school_tier = Column(String(20), nullable=True)

    # 测评结果摘要（便于销售快速判断线索质量）
    overall_score = Column(Integer, nullable=True)
    weak_dimensions = Column(JSON, nullable=True)

    # 来源渠道：report_gate / homepage / manual ...
    source = Column(String(30), default="report_gate")

    # 合规：用户是否勾选同意隐私条款 + 勾选时间
    consent = Column(Integer, default=0)  # 0/1
    consent_at = Column(DateTime, nullable=True)

    # 请求元数据（用于反作弊和溯源）
    ip = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    # 销售跟进状态：new / contacted / converted / invalid
    status = Column(String(20), default="new")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


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

        record.updated_at = datetime.now()
        db.commit()
    finally:
        db.close()


def get_assessment(session_id: str) -> dict | None:
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


def _lead_to_dict(lead: "Lead") -> dict:
    return {
        "id": lead.id,
        "phone": lead.phone,
        "nickname": lead.nickname,
        "major": lead.major,
        "grade": lead.grade,
        "school_tier": lead.school_tier,
        "overall_score": lead.overall_score,
        "weak_dimensions": lead.weak_dimensions,
        "source": lead.source,
        "status": lead.status,
        "notes": lead.notes,
        "session_id": lead.session_id,
        "ip": lead.ip,
        "created_at": lead.created_at.strftime("%Y-%m-%d %H:%M:%S") if lead.created_at else "",
    }


def upsert_lead(data: dict) -> dict:
    """保存或更新一条线索。

    以 (phone, session_id) 为去重键 —— 同一个人同一次测评多次提交手机号只算一次，
    但同一个手机号在不同 session 里会有多条记录（方便看成长曲线）。
    返回保存后的 dict 表示，以及是否为新建记录的标记。
    """
    db = get_db()
    try:
        phone = (data.get("phone") or "").strip()
        session_id = data.get("session_id") or None

        query = db.query(Lead).filter_by(phone=phone)
        if session_id:
            query = query.filter_by(session_id=session_id)
        lead = query.order_by(Lead.created_at.desc()).first()

        is_new = lead is None
        if is_new:
            lead = Lead(phone=phone, session_id=session_id)
            db.add(lead)

        # 覆盖字段（只覆盖非 None 的传入值，避免误清空）
        for field in ("nickname", "major", "grade", "school_tier",
                      "overall_score", "weak_dimensions", "source",
                      "ip", "user_agent"):
            val = data.get(field)
            if val is not None:
                setattr(lead, field, val)

        if data.get("consent"):
            lead.consent = 1
            lead.consent_at = datetime.now()

        db.commit()
        db.refresh(lead)
        result = _lead_to_dict(lead)
        result["is_new"] = is_new
        return result
    finally:
        db.close()


def list_leads(
    limit: int = 100,
    offset: int = 0,
    major: str | None = None,
    grade: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
) -> dict:
    """后台分页查询线索列表"""
    db = get_db()
    try:
        query = db.query(Lead)
        if major:
            query = query.filter(Lead.major == major)
        if grade:
            query = query.filter(Lead.grade == grade)
        if status:
            query = query.filter(Lead.status == status)
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                (Lead.phone.like(like)) | (Lead.nickname.like(like))
            )
        total = query.count()
        rows = (
            query.order_by(Lead.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "items": [_lead_to_dict(r) for r in rows],
        }
    finally:
        db.close()


def update_lead(lead_id: int, status: str | None = None, notes: str | None = None) -> dict | None:
    """更新销售跟进状态或备注"""
    db = get_db()
    try:
        lead = db.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            return None
        if status is not None:
            lead.status = status
        if notes is not None:
            lead.notes = notes
        db.commit()
        db.refresh(lead)
        return _lead_to_dict(lead)
    finally:
        db.close()


def iter_leads_for_export():
    """导出所有线索（生成器，流式写 CSV 避免大内存占用）"""
    db = get_db()
    try:
        for lead in db.query(Lead).order_by(Lead.created_at.desc()).yield_per(200):
            yield _lead_to_dict(lead)
    finally:
        db.close()
