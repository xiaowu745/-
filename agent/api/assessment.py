"""测评相关 API"""

from fastapi import APIRouter, HTTPException

from agent.core import SkillAssessmentAgent, sessions
from models.schemas import (
    QuickAssessmentSubmit,
    DeepAssessmentChat,
    StudentProfile,
    Major,
    Grade,
)

router = APIRouter()
agent = SkillAssessmentAgent()


@router.get("/questions/{major}")
async def get_questions(major: str):
    """获取指定专业的快速自评题目"""
    import json
    from pathlib import Path

    qbank_path = Path(__file__).parent.parent / "knowledge" / "questions" / "quick_assessment.json"
    with open(qbank_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 筛选适用于该专业的题目
    common = data.get("common_questions", [])
    major_specific = data.get(f"{major}_questions", [])
    interest = data.get("interest_questions", [])

    # 过滤适用专业
    applicable_common = [
        q for q in common
        if "all" in q.get("applicable_majors", []) or major in q.get("applicable_majors", [])
    ]

    return {
        "major": major,
        "common_questions": applicable_common,
        "major_questions": major_specific,
        "interest_questions": interest,
        "total_count": len(applicable_common) + len(major_specific) + len(interest),
    }


@router.post("/quick")
async def submit_quick_assessment(submission: QuickAssessmentSubmit):
    """提交快速自评答案，获取初步结果"""
    try:
        result = agent.process_quick_assessment(
            student=submission.student,
            answers=submission.answers,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deep/start/{session_id}")
async def start_deep_assessment(session_id: str):
    """开始深度评估对话"""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在，请先完成快速自评")

    opening = agent.start_deep_assessment(session_id)
    return {
        "session_id": session_id,
        "message": opening,
        "hint": "请根据AI助手的提问回答，对话将持续8-12轮",
    }


@router.post("/deep/chat")
async def deep_assessment_chat(chat: DeepAssessmentChat):
    """深度评估对话"""
    session = sessions.get(chat.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    response = agent.chat_deep_assessment(chat.session_id, chat.message)

    is_complete = session["data"].get("assessment_complete", False)

    return {
        "session_id": chat.session_id,
        "message": response,
        "is_complete": is_complete,
        "hint": "评估完成，可以生成报告" if is_complete else "请继续回答",
    }


@router.get("/demo/start")
async def demo_quick_start():
    """演示入口：快速开始一个测评（无需提交问卷）"""
    # 创建一个模拟的学生档案和得分，用于演示深度对话
    demo_student = StudentProfile(
        nickname="演示同学",
        major=Major.NETWORK_ENGINEERING,
        grade=Grade.SOPHOMORE,
        school_tier="普通本科",
    )

    # 模拟一组快速自评结果
    from models.schemas import DimensionScore, Dimension
    demo_scores = [
        DimensionScore(dimension=Dimension.THEORY, dimension_name="理论基础", score=65, level=4, summary="理论基础扎实"),
        DimensionScore(dimension=Dimension.PROGRAMMING, dimension_name="编程能力", score=45, level=3, summary="编程能力中等"),
        DimensionScore(dimension=Dimension.HARDWARE, dimension_name="硬件实操", score=35, level=2, summary="动手经验较少"),
        DimensionScore(dimension=Dimension.TOOLS, dimension_name="工具掌握", score=40, level=2, summary="工具链需加强"),
        DimensionScore(dimension=Dimension.PROJECT, dimension_name="项目经验", score=25, level=2, summary="项目经验不足"),
        DimensionScore(dimension=Dimension.SOFT_SKILL, dimension_name="职业素养", score=50, level=3, summary="沟通能力一般"),
    ]

    session_id = sessions.create("deep_assessment", {
        "student": demo_student.model_dump(),
        "quick_scores": {ds.dimension.value: ds.score for ds in demo_scores},
        "dimension_scores": [ds.model_dump() for ds in demo_scores],
        "weak_dimensions": ["硬件实操", "项目经验"],
        "directions": [],
    })

    return {
        "session_id": session_id,
        "student": demo_student,
        "quick_scores": {ds.dimension_name: ds.score for ds in demo_scores},
        "message": "演示会话已创建。请调用 POST /api/assessment/deep/start/{session_id} 开始深度对话",
    }
