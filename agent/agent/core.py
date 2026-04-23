"""Agent 核心 - 基于 MiniMax API 的对话管理"""

import json
import re
import uuid
from pathlib import Path
from typing import Optional

from openai import OpenAI

from config import get_settings
from agent.prompts import (
    SYSTEM_PERSONA,
    build_deep_assessment_prompt,
    build_report_prompt,
    build_interview_prompt,
    build_learning_path_prompt,
)
from agent.scoring import (
    calculate_quick_assessment,
    match_directions,
    get_probing_strategy,
)
from models.schemas import (
    StudentProfile, QuickAnswer, DimensionScore,
    AssessmentReport, DirectionMatch, InterviewFeedback,
)
from models.database import save_assessment

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


class SessionStore:
    """简易会话存储（MVP版本用内存，生产用Redis）"""

    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def create(self, session_type: str, data: dict) -> str:
        session_id = str(uuid.uuid4())[:8]
        self._sessions[session_id] = {
            "type": session_type,
            "messages": [],
            "data": data,
        }
        return session_id

    def get(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)

    def add_message(self, session_id: str, role: str, content: str):
        session = self._sessions.get(session_id)
        if session:
            session["messages"].append({"role": role, "content": content})

    def get_messages(self, session_id: str) -> list[dict]:
        session = self._sessions.get(session_id)
        return session["messages"] if session else []


# 全局会话存储
sessions = SessionStore()


class SkillAssessmentAgent:
    """工科技能测评 Agent"""

    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
        )
        self.model = settings.minimax_model

    def _call_llm(self, system: str, messages: list[dict], max_tokens: int = 2000) -> str:
        """调用 MiniMax API（OpenAI 兼容接口）"""
        import re
        full_messages = [{"role": "system", "content": system}] + messages
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=full_messages,
        )
        content = response.choices[0].message.content
        # 过滤掉模型的思考过程 <think>...</think>
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return content

    # ============================================================
    # 快速测评
    # ============================================================

    def process_quick_assessment(
        self, student: StudentProfile, answers: list[QuickAnswer]
    ) -> dict:
        """处理快速自评结果"""
        dimension_scores, overall_score, weak_dims = calculate_quick_assessment(
            student, answers
        )

        # 匹配推荐方向
        directions = match_directions(student, dimension_scores)

        # 创建深度评估会话
        session_id = sessions.create("deep_assessment", {
            "student": student.model_dump(),
            "quick_scores": {ds.dimension.value: ds.score for ds in dimension_scores},
            "dimension_scores": [ds.model_dump() for ds in dimension_scores],
            "weak_dimensions": weak_dims,
            "directions": [d.model_dump() for d in directions],
        })

        # 持久化到数据库
        try:
            save_assessment(session_id, {
                "student": student.model_dump(),
                "quick_answers": [a.model_dump() for a in answers],
                "dimension_scores": [ds.model_dump() for ds in dimension_scores],
                "overall_score": overall_score,
                "weak_dimensions": weak_dims,
                "recommended_directions": [d.model_dump() for d in directions],
                "status": "quick_done",
            })
        except Exception:
            pass  # MVP阶段数据库异常不阻塞主流程

        return {
            "session_id": session_id,
            "dimension_scores": dimension_scores,
            "overall_score": overall_score,
            "weak_dimensions": weak_dims,
            "preliminary_directions": directions,
            "next_step": "建议进入深度评估对话，获取更精准的分析",
        }

    # ============================================================
    # 深度评估对话
    # ============================================================

    def start_deep_assessment(self, session_id: str) -> str:
        """开始深度评估对话"""
        session = sessions.get(session_id)
        if not session:
            return "会话不存在，请重新开始测评"

        data = session["data"]
        student = data["student"]
        quick_scores = data["quick_scores"]
        weak_dims = data["weak_dimensions"]

        # 获取追问策略
        dimension_scores = [DimensionScore(**ds) for ds in data["dimension_scores"]]
        overall = sum(quick_scores.values()) // len(quick_scores)
        probing_strategy = get_probing_strategy(dimension_scores, overall)

        # 构建系统 prompt
        system_prompt = SYSTEM_PERSONA + "\n\n" + build_deep_assessment_prompt(
            student_profile=student,
            quick_scores=quick_scores,
            weak_dimensions=weak_dims,
            probing_strategy=probing_strategy,
        )

        # 生成开场白
        opening = self._call_llm(
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": "请开始深度评估对话。先根据我的快速自评结果，友好地做一个开场引入，然后开始提问。",
            }],
        )

        # 存储 system prompt 以便后续对话使用
        session["data"]["system_prompt"] = system_prompt
        sessions.add_message(session_id, "assistant", opening)

        return opening

    def chat_deep_assessment(self, session_id: str, user_message: str) -> str:
        """深度评估对话的一轮交互"""
        session = sessions.get(session_id)
        if not session:
            return "会话不存在，请重新开始测评"

        system_prompt = session["data"].get("system_prompt", SYSTEM_PERSONA)

        # 添加用户消息
        sessions.add_message(session_id, "user", user_message)
        messages = sessions.get_messages(session_id)

        # 调用 Claude
        response = self._call_llm(
            system=system_prompt,
            messages=messages,
            max_tokens=1500,
        )

        sessions.add_message(session_id, "assistant", response)

        # 检查是否评估完成
        if "[ASSESSMENT_COMPLETE]" in response:
            self._process_assessment_completion(session_id, response)

        return response

    def _process_assessment_completion(self, session_id: str, response: str):
        """处理评估完成，解析结果"""
        session = sessions.get(session_id)
        if not session:
            return

        # 解析评估结果
        match = re.search(
            r"\[ASSESSMENT_COMPLETE\](.*?)\[/ASSESSMENT_COMPLETE\]",
            response,
            re.DOTALL,
        )
        if match:
            result_text = match.group(1).strip()
            # 解析各项评分
            parsed = {}
            for line in result_text.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    parsed[key.strip()] = value.strip()

            session["data"]["deep_assessment_result"] = parsed
            session["data"]["assessment_complete"] = True

    # ============================================================
    # 报告生成
    # ============================================================

    def generate_report(self, session_id: str) -> str:
        """生成完整测评报告"""
        session = sessions.get(session_id)
        if not session:
            return "会话不存在"

        data = session["data"]
        student = data["student"]
        dimension_scores = data.get("deep_assessment_result", data["quick_scores"])
        directions = data.get("directions", [])

        # 加载专业知识库
        major_knowledge = {}
        major_file = KNOWLEDGE_DIR / "majors" / f"{student['major']}.json"
        if major_file.exists():
            with open(major_file, "r", encoding="utf-8") as f:
                major_knowledge = json.load(f)

        # 构建报告 prompt
        report_prompt = build_report_prompt(
            student_profile=student,
            dimension_scores=dimension_scores,
            strengths=data.get("deep_assessment_result", {}).get("strengths", "").split("|"),
            weaknesses=data.get("deep_assessment_result", {}).get("weaknesses", "").split("|"),
            recommended_directions=[d.get("direction_name", "") for d in directions] if isinstance(directions[0], dict) else [],
            major_knowledge=major_knowledge,
        )

        system = SYSTEM_PERSONA + "\n\n" + report_prompt

        report = self._call_llm(
            system=system,
            messages=[{
                "role": "user",
                "content": "请生成我的完整技能测评报告。",
            }],
            max_tokens=3000,
        )

        return report

    # ============================================================
    # 面试模拟
    # ============================================================

    def start_interview(
        self,
        session_id: str,
        target_position: str,
        interview_type: str = "technical",
    ) -> str:
        """开始面试模拟"""
        parent_session = sessions.get(session_id)
        student = parent_session["data"]["student"] if parent_session else {}
        assessment = parent_session["data"].get("deep_assessment_result", {}) if parent_session else {}

        # 加载面试题库（从知识库中获取相关问题）
        interview_questions = self._load_interview_questions(target_position)

        # 构建面试 prompt
        system = SYSTEM_PERSONA + "\n\n" + build_interview_prompt(
            target_position=target_position,
            student_profile=student,
            assessment_summary=str(assessment),
            interview_questions=interview_questions,
            interview_type=interview_type,
        )

        # 创建面试会话
        interview_session_id = sessions.create("interview", {
            "parent_session": session_id,
            "target_position": target_position,
            "interview_type": interview_type,
            "system_prompt": system,
        })

        # 面试官开场
        opening = self._call_llm(
            system=system,
            messages=[{
                "role": "user",
                "content": "面试开始，请面试官做自我介绍并开始提问。",
            }],
        )

        sessions.add_message(interview_session_id, "assistant", opening)
        return interview_session_id, opening

    def chat_interview(self, interview_session_id: str, user_message: str) -> str:
        """面试模拟的一轮对话"""
        session = sessions.get(interview_session_id)
        if not session:
            return "面试会话不存在"

        system_prompt = session["data"]["system_prompt"]
        sessions.add_message(interview_session_id, "user", user_message)
        messages = sessions.get_messages(interview_session_id)

        response = self._call_llm(
            system=system_prompt,
            messages=messages,
            max_tokens=1500,
        )

        sessions.add_message(interview_session_id, "assistant", response)
        return response

    def _load_interview_questions(self, target_position: str) -> str:
        """加载面试相关的问题方向"""
        # 简化实现，后续可以从题库中精准匹配
        position_questions = {
            "网络工程师": """
- TCP三次握手/四次挥手
- VLAN原理和配置
- OSPF/BGP基础
- 网络故障排查思路
- NAT/ACL配置
- 综合布线基础知识
- 项目经历深入追问""",
            "PLC工程师": """
- PLC工作原理
- 梯形图编程基础
- 伺服/变频器控制
- 故障排查经验
- 项目经历追问""",
            "嵌入式工程师": """
- C语言指针、内存管理
- STM32定时器/中断/DMA
- 通信协议(SPI/I2C/UART)
- RTOS基础
- 项目经历追问""",
            "系统集成工程师": """
- 弱电智能化子系统
- 综合布线规范
- 网络设备配置
- 项目管理基础
- 客户需求分析""",
        }
        return position_questions.get(target_position, "根据岗位JD通用技术面试题")

    # ============================================================
    # 学习路径
    # ============================================================

    def generate_learning_path(
        self,
        session_id: str,
        target_direction: str,
    ) -> str:
        """生成个性化学习路径"""
        session = sessions.get(session_id)
        if not session:
            return "会话不存在"

        data = session["data"]
        student = data["student"]
        scores = data.get("deep_assessment_result", data["quick_scores"])

        # 加载目标方向的技能要求
        major_file = KNOWLEDGE_DIR / "majors" / f"{student['major']}.json"
        target_requirements = {}
        if major_file.exists():
            with open(major_file, "r", encoding="utf-8") as f:
                major_data = json.load(f)
                for d in major_data.get("career_directions", []):
                    if d["name"] == target_direction:
                        target_requirements = d
                        break

        system = SYSTEM_PERSONA + "\n\n" + build_learning_path_prompt(
            major=student["major"],
            grade=student["grade"],
            current_scores=scores,
            target_direction=target_direction,
            target_requirements=target_requirements,
        )

        path = self._call_llm(
            system=system,
            messages=[{
                "role": "user",
                "content": f"请根据我的情况，生成从当前水平到「{target_direction}」这个方向的个性化学习路径。",
            }],
            max_tokens=3000,
        )

        return path
