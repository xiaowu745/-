"""评分算法与方向匹配引擎"""

import json
from pathlib import Path
from models.schemas import (
    Dimension, DimensionScore, DirectionMatch,
    QuickAnswer, StudentProfile, Major
)

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"

# 维度中文名映射
DIMENSION_NAMES = {
    Dimension.THEORY: "理论基础",
    Dimension.PROGRAMMING: "编程能力",
    Dimension.HARDWARE: "硬件实操",
    Dimension.TOOLS: "工具掌握",
    Dimension.PROJECT: "项目经验",
    Dimension.SOFT_SKILL: "职业素养",
}

# 各专业维度权重（不同专业对各维度的侧重不同）
MAJOR_WEIGHTS = {
    Major.NETWORK_ENGINEERING: {
        Dimension.THEORY: 0.20,
        Dimension.PROGRAMMING: 0.10,
        Dimension.HARDWARE: 0.25,
        Dimension.TOOLS: 0.20,
        Dimension.PROJECT: 0.15,
        Dimension.SOFT_SKILL: 0.10,
    },
    Major.COMPUTER_SCIENCE: {
        Dimension.THEORY: 0.15,
        Dimension.PROGRAMMING: 0.30,
        Dimension.HARDWARE: 0.05,
        Dimension.TOOLS: 0.20,
        Dimension.PROJECT: 0.20,
        Dimension.SOFT_SKILL: 0.10,
    },
    Major.AUTOMATION: {
        Dimension.THEORY: 0.20,
        Dimension.PROGRAMMING: 0.15,
        Dimension.HARDWARE: 0.25,
        Dimension.TOOLS: 0.15,
        Dimension.PROJECT: 0.15,
        Dimension.SOFT_SKILL: 0.10,
    },
    Major.ELECTRONIC_INFO: {
        Dimension.THEORY: 0.20,
        Dimension.PROGRAMMING: 0.15,
        Dimension.HARDWARE: 0.25,
        Dimension.TOOLS: 0.15,
        Dimension.PROJECT: 0.15,
        Dimension.SOFT_SKILL: 0.10,
    },
    Major.IOT: {
        Dimension.THEORY: 0.15,
        Dimension.PROGRAMMING: 0.20,
        Dimension.HARDWARE: 0.20,
        Dimension.TOOLS: 0.15,
        Dimension.PROJECT: 0.20,
        Dimension.SOFT_SKILL: 0.10,
    },
}

# 默认权重
DEFAULT_WEIGHTS = {
    Dimension.THEORY: 0.18,
    Dimension.PROGRAMMING: 0.18,
    Dimension.HARDWARE: 0.18,
    Dimension.TOOLS: 0.16,
    Dimension.PROJECT: 0.18,
    Dimension.SOFT_SKILL: 0.12,
}


def score_to_level(score: int) -> int:
    """将百分制得分转换为1-5等级"""
    if score >= 81:
        return 5
    elif score >= 61:
        return 4
    elif score >= 41:
        return 3
    elif score >= 21:
        return 2
    else:
        return 1


def calculate_dimension_score(answers: list[QuickAnswer], dimension: Dimension, question_bank: dict) -> int:
    """计算单个维度的得分（0-100）"""
    # 找出该维度的所有题目
    all_questions = (
        question_bank.get("common_questions", [])
        + question_bank.get("network_engineering_questions", [])
        + question_bank.get("automation_questions", [])
    )

    dimension_questions = [q for q in all_questions if q["dimension"] == dimension.value]
    answered_ids = {a.question_id for a in answers}

    scores = []
    for q in dimension_questions:
        if q["id"] in answered_ids:
            answer = next(a for a in answers if a.question_id == q["id"])
            option_score = q["options"][answer.selected_option]["score"]
            scores.append(option_score)

    if not scores:
        return 0

    # 选项分值1-4，转换为0-100
    avg = sum(scores) / len(scores)
    return int((avg / 4.0) * 100)


def calculate_quick_assessment(
    student: StudentProfile,
    answers: list[QuickAnswer],
) -> tuple[list[DimensionScore], int, list[str]]:
    """
    计算快速自评结果

    Returns:
        dimension_scores: 各维度得分
        overall_score: 综合得分
        weak_dimensions: 薄弱维度列表
    """
    # 加载题库
    qbank_path = KNOWLEDGE_DIR / "questions" / "quick_assessment.json"
    with open(qbank_path, "r", encoding="utf-8") as f:
        question_bank = json.load(f)

    # 获取专业对应的权重
    weights = MAJOR_WEIGHTS.get(student.major, DEFAULT_WEIGHTS)

    # 计算各维度得分
    dimension_scores = []
    for dim in Dimension:
        score = calculate_dimension_score(answers, dim, question_bank)
        dimension_scores.append(DimensionScore(
            dimension=dim,
            dimension_name=DIMENSION_NAMES[dim],
            score=score,
            level=score_to_level(score),
            summary=_get_dimension_summary(dim, score),
        ))

    # 计算加权综合得分
    overall = sum(
        ds.score * weights.get(ds.dimension, 1 / 6)
        for ds in dimension_scores
    )
    overall_score = int(overall)

    # 找出薄弱维度（得分低于40的）
    weak_dimensions = [
        ds.dimension_name
        for ds in dimension_scores
        if ds.score < 40
    ]

    # 如果没有低于40的，取最低的2个
    if not weak_dimensions:
        sorted_dims = sorted(dimension_scores, key=lambda x: x.score)
        weak_dimensions = [sorted_dims[0].dimension_name, sorted_dims[1].dimension_name]

    return dimension_scores, overall_score, weak_dimensions


def match_directions(
    student: StudentProfile,
    dimension_scores: list[DimensionScore],
    interest_tags: list[str] | None = None,
) -> list[DirectionMatch]:
    """
    匹配推荐方向

    Returns:
        TOP 3 推荐方向
    """
    # 加载专业知识库
    major_file = KNOWLEDGE_DIR / "majors" / f"{student.major.value}.json"
    if not major_file.exists():
        return []

    with open(major_file, "r", encoding="utf-8") as f:
        major_data = json.load(f)

    score_map = {ds.dimension.value: ds.score for ds in dimension_scores}

    # 为每个方向计算匹配度
    matches = []
    for direction in major_data.get("career_directions", []):
        match_score = _calculate_direction_match(
            direction, score_map, student, interest_tags
        )
        reasons = _generate_match_reasons(direction, score_map, student)

        matches.append(DirectionMatch(
            rank=0,  # 后面排序后赋值
            direction_name=direction["name"],
            match_score=match_score,
            reasons=reasons,
            salary_range=f'{direction["salary"]["entry"]} → {direction["salary"]["mid"]} → {direction["salary"]["senior"]}',
            trend="上升",  # 简化处理，后续可以从数据库读取
        ))

    # 排序取 TOP 3
    matches.sort(key=lambda x: x.match_score, reverse=True)
    for i, m in enumerate(matches[:3]):
        m.rank = i + 1

    return matches[:3]


def _calculate_direction_match(
    direction: dict,
    score_map: dict,
    student: StudentProfile,
    interest_tags: list[str] | None,
) -> int:
    """计算单个方向的匹配度"""
    base_score = 50  # 基础分

    # 技能匹配加分（最多+30）
    required_skills = direction.get("required_skills", [])
    # 简化：根据相关维度的得分来估算技能匹配度
    skill_bonus = 0
    avg_score = sum(score_map.values()) / len(score_map) if score_map else 0
    skill_bonus = int(avg_score * 0.3)

    # 兴趣匹配加分（最多+15）
    interest_bonus = 0
    if interest_tags:
        direction_traits = direction.get("traits", [])
        # 简化匹配逻辑
        interest_bonus = 10 if interest_tags else 0

    # 现实约束调整
    constraint_adjustment = 0
    traits = direction.get("traits", [])
    if not student.accept_travel and "需出差" in " ".join(traits):
        constraint_adjustment -= 15
    if not student.accept_travel and "需出差调试" in " ".join(traits):
        constraint_adjustment -= 10

    total = base_score + skill_bonus + interest_bonus + constraint_adjustment
    return max(0, min(100, total))


def _generate_match_reasons(
    direction: dict,
    score_map: dict,
    student: StudentProfile,
) -> list[str]:
    """生成匹配原因说明"""
    reasons = []

    # 根据高分维度生成原因
    if score_map.get("theory", 0) >= 60:
        reasons.append("你的理论基础扎实，为这个方向打下了好底子")
    if score_map.get("programming", 0) >= 60:
        reasons.append("你的编程能力是这个方向的加分项")
    if score_map.get("hardware", 0) >= 60:
        reasons.append("你的动手实操能力匹配这个方向的要求")
    if score_map.get("project", 0) >= 60:
        reasons.append("你有项目经验，入行会更顺利")

    # 添加方向特点
    salary = direction.get("salary", {})
    if salary.get("senior", ""):
        reasons.append(f"该方向资深薪资可达 {salary['senior']}")

    traits = direction.get("traits", [])
    if traits:
        reasons.append(f"方向特点：{'、'.join(traits[:2])}")

    return reasons[:4]  # 最多4条原因


def _get_dimension_summary(dimension: Dimension, score: int) -> str:
    """根据维度和得分生成简要评价"""
    level = score_to_level(score)

    summaries = {
        Dimension.THEORY: {
            1: "理论基础薄弱，核心概念还需要系统学习",
            2: "有一定理论基础，但部分核心概念还不够扎实",
            3: "理论基础中等，能理解大部分专业概念",
            4: "理论基础扎实，能深入分析和应用",
            5: "理论功底深厚，具备设计和创新能力",
        },
        Dimension.PROGRAMMING: {
            1: "编程刚起步，需要大量练习",
            2: "能写简单程序，但独立开发还有差距",
            3: "编程能力中等，能独立完成小型项目",
            4: "编程能力较强，能处理中等复杂度的开发任务",
            5: "编程能力突出，具备架构设计级别的能力",
        },
        Dimension.HARDWARE: {
            1: "动手经验很少，需要从基础实操开始",
            2: "有基础动手能力，但离独立操作还有距离",
            3: "能在指导下完成实操任务，有一定调试经验",
            4: "动手能力强，能独立完成实训项目和故障排查",
            5: "实操经验丰富，能处理各种复杂的现场问题",
        },
        Dimension.TOOLS: {
            1: "行业工具几乎没接触过",
            2: "了解一些工具但不熟练",
            3: "能使用核心工具完成基本任务",
            4: "熟练使用行业工具链",
            5: "精通各类工具，能选择和优化工具组合",
        },
        Dimension.PROJECT: {
            1: "还没有独立的项目经验，需要尽快开始",
            2: "有课程设计经验，但缺少完整的独立项目",
            3: "有1-2个完整项目，能基本说清技术细节",
            4: "项目经验丰富，有竞赛或实习项目经历",
            5: "有多个高质量项目，具备企业级项目经验",
        },
        Dimension.SOFT_SKILL: {
            1: "沟通和协作能力需要提升",
            2: "有基本的团队协作能力",
            3: "能清楚表达技术想法，有一定的团队协作经验",
            4: "沟通表达能力好，有带队或汇报经验",
            5: "综合职业素养突出，具备项目管理和技术领导力",
        },
    }

    return summaries.get(dimension, {}).get(level, "评估中")


def get_probing_strategy(dimension_scores: list[DimensionScore], overall_score: int) -> str:
    """根据快速自评结果确定深度追问策略"""
    strategies_path = KNOWLEDGE_DIR / "questions" / "deep_assessment.json"
    with open(strategies_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    score_map = {ds.dimension.value: ds.score for ds in dimension_scores}

    matched_strategies = []
    for strategy in data["strategies"]:
        trigger = strategy["trigger"]
        # 简化的条件匹配
        if _evaluate_trigger(trigger, score_map, overall_score):
            matched_strategies.append(strategy)

    if not matched_strategies:
        return "综合评估，全面了解学生情况"

    # 组合所有匹配策略的追问问题
    result_lines = []
    for s in matched_strategies:
        result_lines.append(f"假设：{s['hypothesis']}")
        result_lines.append(f"追问方向：")
        for q in s["probing_questions"]:
            result_lines.append(f"  - {q}")
        result_lines.append(f"建议：{s['recommendation']}")
        result_lines.append("")

    return "\n".join(result_lines)


def _evaluate_trigger(trigger: str, score_map: dict, overall_score: int) -> bool:
    """简化的触发条件评估"""
    trigger_lower = trigger.lower()

    if "overall_score >= 70" in trigger_lower and overall_score >= 70:
        return True
    if "overall_score <= 30" in trigger_lower and overall_score <= 30:
        return True
    if "project_score <= 1" in trigger_lower and score_map.get("project", 50) <= 25:
        return True
    if ("theory_score >= 3" in trigger_lower and "hardware_score <= 2" in trigger_lower
            and score_map.get("theory", 0) >= 60 and score_map.get("hardware", 50) <= 40):
        return True
    if ("hardware_score >= 3" in trigger_lower and "theory_score <= 2" in trigger_lower
            and score_map.get("hardware", 0) >= 60 and score_map.get("theory", 50) <= 40):
        return True
    if ("programming_score >= 3" in trigger_lower and "tools_score <= 2" in trigger_lower
            and score_map.get("programming", 0) >= 60 and score_map.get("tools", 50) <= 40):
        return True

    return False
