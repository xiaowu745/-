"""数据模型定义"""

from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


# ============ 枚举 ============

class Major(str, Enum):
    """支持的专业"""
    COMPUTER_SCIENCE = "computer_science"       # 计算机科学与技术
    SOFTWARE_ENGINEERING = "software_engineering" # 软件工程
    NETWORK_ENGINEERING = "network_engineering"  # 网络工程
    ELECTRONIC_INFO = "electronic_info"          # 电子信息工程
    COMMUNICATION = "communication"             # 通信工程
    AUTOMATION = "automation"                   # 自动化
    ELECTRICAL = "electrical"                   # 电气工程
    IOT = "iot"                                 # 物联网工程
    MECHANICAL = "mechanical"                   # 机械设计/机电一体化
    AI = "ai"                                   # 人工智能


class Grade(str, Enum):
    """年级"""
    FRESHMAN = "freshman"     # 大一
    SOPHOMORE = "sophomore"   # 大二
    JUNIOR = "junior"         # 大三
    SENIOR = "senior"         # 大四


class Dimension(str, Enum):
    """评估维度"""
    THEORY = "theory"           # 理论基础
    PROGRAMMING = "programming" # 编程能力
    HARDWARE = "hardware"       # 硬件实操
    TOOLS = "tools"             # 工具掌握
    PROJECT = "project"         # 项目经验
    SOFT_SKILL = "soft_skill"   # 职业素养


# ============ 请求模型 ============

class StudentProfile(BaseModel):
    """学生基本信息"""
    nickname: str = Field(..., description="昵称", max_length=20)
    major: Major = Field(..., description="专业")
    grade: Grade = Field(..., description="年级")
    school_tier: str = Field(default="普通本科", description="学校层次: 985/211/普通本科/专科")
    city_preference: str = Field(default="", description="意向就业城市")
    salary_expectation: str = Field(default="", description="期望薪资范围")
    accept_travel: bool = Field(default=True, description="是否接受出差")


class QuickAnswer(BaseModel):
    """快速自评单题回答"""
    question_id: str
    selected_option: int = Field(..., ge=0, le=3, description="选项索引 0-3")


class QuickAssessmentSubmit(BaseModel):
    """快速自评提交"""
    student: StudentProfile
    answers: list[QuickAnswer] = Field(..., min_length=1)


class ChatMessage(BaseModel):
    """对话消息"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class DeepAssessmentChat(BaseModel):
    """深度评估对话请求"""
    session_id: str
    message: str


class InterviewRequest(BaseModel):
    """面试模拟请求"""
    session_id: str
    target_position: str = Field(..., description="目标岗位")
    interview_type: str = Field(default="technical", description="面试类型: technical/hr/project")
    message: str = Field(default="", description="学生回答")


# ============ 响应模型 ============

class DimensionScore(BaseModel):
    """单维度评分"""
    dimension: Dimension
    dimension_name: str
    score: int = Field(..., ge=0, le=100)
    level: int = Field(..., ge=1, le=5, description="等级 1-5")
    summary: str = Field(..., description="该维度的文字评价")


class DirectionMatch(BaseModel):
    """方向匹配结果"""
    rank: int
    direction_name: str
    match_score: int = Field(..., ge=0, le=100)
    reasons: list[str]
    salary_range: str
    trend: str = Field(..., description="上升/稳定/下降")


class AssessmentReport(BaseModel):
    """测评报告"""
    report_id: str
    student: StudentProfile
    overall_score: int = Field(..., ge=0, le=100)
    percentile: int = Field(..., ge=0, le=100, description="超过百分之多少的同专业学生")
    dimension_scores: list[DimensionScore]
    strengths: list[str] = Field(..., description="优势项")
    weaknesses: list[str] = Field(..., description="待提升项")
    recommended_directions: list[DirectionMatch]
    learning_path_summary: str
    next_steps: list[str] = Field(..., description="建议的下一步行动")
    created_at: datetime = Field(default_factory=datetime.now)


class QuickAssessmentResult(BaseModel):
    """快速自评结果（触发深度对话前的中间结果）"""
    session_id: str
    dimension_scores: list[DimensionScore]
    overall_score: int
    weak_dimensions: list[str] = Field(..., description="需要深度评估的薄弱维度")
    next_step: str = Field(default="deep_assessment", description="建议下一步")


class InterviewFeedback(BaseModel):
    """面试模拟反馈"""
    overall_rating: int = Field(..., ge=1, le=10)
    tech_depth: int = Field(..., ge=0, le=100)
    expression: int = Field(..., ge=0, le=100)
    adaptability: int = Field(..., ge=0, le=100)
    suggestions: list[str]
    recommended_practice: list[str]
