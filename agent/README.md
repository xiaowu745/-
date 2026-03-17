# 工科导航 - 技能测评 Agent

基于 AI 的工科大学生技能测评与职业发展规划平台。

## 功能模块

| 模块 | 说明 | API |
|------|------|-----|
| 快速测评 | 20题自评问卷，3分钟完成 | `POST /api/assessment/quick` |
| 深度对话 | AI 追问验证，10-15分钟 | `POST /api/assessment/deep/chat` |
| 测评报告 | 雷达图 + 方向推荐 + 路径规划 | `POST /api/report/generate/{id}` |
| 面试模拟 | 技术面/HR面/项目答辩 | `POST /api/interview/start` |
| 自由问答 | 职业规划相关任意提问 | `POST /api/chat/free` |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY

# 3. 启动服务
uvicorn main:app --reload --port 8000

# 4. 访问 API 文档
# http://localhost:8000/docs
```

## 演示流程

```bash
# 1. 获取测评题目
GET /api/assessment/questions/network_engineering

# 2. 快速开始演示（跳过问卷）
GET /api/assessment/demo/start

# 3. 开始深度评估对话
POST /api/assessment/deep/start/{session_id}

# 4. 对话交互
POST /api/assessment/deep/chat
{"session_id": "xxx", "message": "你的回答"}

# 5. 生成报告
POST /api/report/generate/{session_id}

# 6. 面试模拟
POST /api/interview/start
{"target_position": "网络工程师", "interview_type": "technical"}
```

## 项目结构

```
agent/
├── main.py              # FastAPI 入口
├── config.py            # 配置管理
├── api/                 # API 路由
│   ├── assessment.py    # 测评接口
│   ├── report.py        # 报告接口
│   ├── interview.py     # 面试模拟接口
│   └── chat.py          # 自由问答接口
├── agent/               # Agent 核心
│   ├── core.py          # 对话管理 + Claude API 调用
│   ├── prompts.py       # Prompt 模板体系
│   └── scoring.py       # 评分算法 + 方向匹配
├── knowledge/           # 知识库
│   ├── majors/          # 专业数据（JSON）
│   └── questions/       # 题库数据（JSON）
├── models/              # 数据模型
│   └── schemas.py       # Pydantic 模型
└── templates/           # 报告模板（预留）
```

## 覆盖专业

- 网络工程 ✅ (知识库已完成)
- 自动化 ✅ (知识库已完成)
- 电子信息工程 ✅ (知识库已完成)
- 物联网工程 ✅ (知识库已完成)
- 计算机科学（待补充）
- 机械/机电（待补充）

## 技术栈

- **后端**: Python + FastAPI
- **AI**: Claude API (Anthropic)
- **数据模型**: Pydantic v2
- **知识库**: JSON 文件（MVP）→ 数据库（生产）
- **会话存储**: 内存（MVP）→ Redis（生产）
