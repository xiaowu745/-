"""报告生成 API"""

from fastapi import APIRouter, HTTPException

from agent.core import SkillAssessmentAgent, sessions

router = APIRouter()
agent = SkillAssessmentAgent()


@router.post("/generate/{session_id}")
async def generate_report(session_id: str):
    """根据测评结果生成完整报告"""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    report_text = agent.generate_report(session_id)

    return {
        "session_id": session_id,
        "report": report_text,
        "data": {
            "student": session["data"].get("student"),
            "dimension_scores": session["data"].get("dimension_scores"),
            "directions": session["data"].get("directions"),
        },
    }


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
