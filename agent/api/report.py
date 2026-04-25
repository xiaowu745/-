"""报告生成 API"""

from fastapi import APIRouter, HTTPException

from agent.core import SkillAssessmentAgent, sessions
from models.database import get_db, AssessmentRecord

router = APIRouter()
agent = SkillAssessmentAgent()


@router.post("/generate/{session_id}")
async def generate_report(session_id: str):
    """根据测评结果生成完整报告"""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    report_text = agent.generate_report(session_id)

    try:
        from models.database import save_assessment
        save_assessment(session_id, {
            "report_text": report_text,
            "status": "report_generated",
        })
    except Exception:
        pass

    return {
        "session_id": session_id,
        "report": report_text,
        "data": {
            "student": session["data"].get("student"),
            "dimension_scores": session["data"].get("dimension_scores"),
            "directions": session["data"].get("directions"),
        },
    }


@router.get("/by-phone/{phone}")
async def get_reports_by_phone(phone: str):
    """根据手机号查询测评报告"""
    db = get_db()
    try:
        records = db.query(AssessmentRecord).filter_by(phone=phone).order_by(
            AssessmentRecord.created_at.desc()
        ).limit(20).all()

        return {
            "reports": [
                {
                    "session_id": r.session_id,
                    "nickname": r.nickname,
                    "major": r.major,
                    "grade": r.grade,
                    "overall_score": r.overall_score,
                    "status": r.status,
                    "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                }
                for r in records
            ]
        }
    finally:
        db.close()


@router.get("/view/{session_id}")
async def view_report(session_id: str):
    """查看单个测评报告详情"""
    db = get_db()
    try:
        record = db.query(AssessmentRecord).filter_by(session_id=session_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="报告不存在")

        return {
            "session_id": record.session_id,
            "nickname": record.nickname,
            "major": record.major,
            "grade": record.grade,
            "overall_score": record.overall_score,
            "dimension_scores": record.dimension_scores,
            "weak_dimensions": record.weak_dimensions,
            "report": record.report_text,
            "status": record.status,
            "created_at": record.created_at.strftime("%Y-%m-%d %H:%M") if record.created_at else "",
        }
    finally:
        db.close()


@router.post("/learning-path/{session_id}")
async def generate_learning_path(session_id: str, target_direction: str):
    """生成个性化学习路径"""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    path = agent.generate_learning_path(session_id, target_direction)

    return {
        "session_id": session_id,
        "target_direction": target_direction,
        "learning_path": path,
    }
