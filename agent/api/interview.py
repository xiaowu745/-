"""面试模拟 API"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.core import SkillAssessmentAgent, sessions

router = APIRouter()
agent = SkillAssessmentAgent()


class InterviewStartRequest(BaseModel):
    session_id: str = ""
    target_position: str
    interview_type: str = "technical"


class InterviewChatRequest(BaseModel):
    interview_session_id: str
    message: str


@router.post("/start")
async def start_interview(req: InterviewStartRequest):
    """开始面试模拟"""
    interview_session_id, opening = agent.start_interview(
        session_id=req.session_id,
        target_position=req.target_position,
        interview_type=req.interview_type,
    )

    return {
        "interview_session_id": interview_session_id,
        "message": opening,
        "target_position": req.target_position,
        "interview_type": req.interview_type,
        "hint": "请回答面试官的问题。如需结束面试，发送'面试结束'。",
    }


@router.post("/chat")
async def interview_chat(req: InterviewChatRequest):
    """面试对话"""
    session = sessions.get(req.interview_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="面试会话不存在")

    response = agent.chat_interview(req.interview_session_id, req.message)

    is_complete = "[INTERVIEW_FEEDBACK]" in response

    return {
        "interview_session_id": req.interview_session_id,
        "message": response,
        "is_complete": is_complete,
    }
