"""通用 AI 对话 API - 用于自由问答"""

from fastapi import APIRouter
from pydantic import BaseModel

from agent.core import SkillAssessmentAgent, sessions
from agent.prompts import SYSTEM_PERSONA

router = APIRouter()
agent = SkillAssessmentAgent()

FREE_CHAT_SYSTEM = SYSTEM_PERSONA + """

## 当前模式：自由问答

学生可以问你任何关于工科就业、专业发展、考证、实习的问题。
你根据自己的知识和经验来回答。

## 回答原则
- 基于15年一线工程经验和10年高校实训经验来回答
- 给出具体的建议和数据，不说空话
- 如果不确定的信息，要坦诚说明
- 适当引导学生去做测评，了解自己的水平
- 不要推荐具体的培训机构（除了我们自己的实训营）

## 可以回答的问题类型
- XX专业能做什么工作？
- XX岗位薪资多少？发展怎么样？
- 考什么证有用？
- 考研还是就业？
- 大学应该怎么规划？
- 某某技能怎么学？
- 面试需要注意什么？
- 简历怎么写？
- 等等"""


class FreeChatRequest(BaseModel):
    message: str
    session_id: str = ""


@router.post("/free")
async def free_chat(req: FreeChatRequest):
    """自由问答 - 不需要先做测评也能使用"""
    if not req.session_id:
        session_id = sessions.create("free_chat", {"system_prompt": FREE_CHAT_SYSTEM})
    else:
        session_id = req.session_id

    session = sessions.get(session_id)
    if not session:
        session_id = sessions.create("free_chat", {"system_prompt": FREE_CHAT_SYSTEM})
        session = sessions.get(session_id)

    sessions.add_message(session_id, "user", req.message)
    messages = sessions.get_messages(session_id)

    response = agent._call_claude(
        system=FREE_CHAT_SYSTEM,
        messages=messages,
        max_tokens=1500,
    )

    sessions.add_message(session_id, "assistant", response)

    return {
        "session_id": session_id,
        "message": response,
    }
