# 荆工智匠 - 技能测评 Agent

基于 AI 的工科大学生技能测评与职业发展规划平台。

## 功能模块

| 模块 | 说明 | API |
|------|------|-----|
| 快速测评 | 12-20题自评问卷，3分钟完成 | `POST /api/assessment/quick` |
| 深度对话 | AI 追问验证，10-15分钟 | `POST /api/assessment/deep/chat` |
| 测评报告 | 雷达图 + 方向推荐 + 路径规划 | `POST /api/report/generate/{id}` |
| 面试模拟 | 技术面/HR面/项目答辩 | `POST /api/interview/start` |
| 自由问答 | 职业规划相关任意提问 | `POST /api/chat/free` |
| 用户系统 | 注册/登录/历史记录/成长曲线 | `POST /api/user/register` |
| H5 前端 | 完整可交互测评页面 | `GET /` |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY

# 3. 启动服务
uvicorn main:app --reload --port 8000

# 4. 浏览器打开
# 前端页面: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

**注意**：即使不配置 API Key，前端的快速测评（本地计算）和雷达图也可以正常使用。配置 API Key 后才可使用 AI 深度对话、报告生成、面试模拟等功能。

## 项目结构

```
agent/
├── main.py              # FastAPI 入口 + 静态文件服务
├── config.py            # 配置管理
├── frontend/            # H5 前端
│   ├── index.html       # 主页面（SPA）
│   ├── style.css        # 样式（移动端优先）
│   └── app.js           # 交互逻辑（含本地兜底计算）
├── api/                 # API 路由
│   ├── assessment.py    # 测评接口
│   ├── report.py        # 报告 + 学习路径接口
│   ├── interview.py     # 面试模拟接口
│   ├── chat.py          # 自由问答接口
│   └── user.py          # 用户注册/登录/历史
├── agent/               # Agent 核心
│   ├── core.py          # 对话管理 + Claude API 调用
│   ├── prompts.py       # 5层 Prompt 模板体系
│   └── scoring.py       # 6维度评分算法 + 方向匹配引擎
├── knowledge/           # 知识库（6个专业 + 题库）
│   ├── majors/          # 专业数据（JSON）
│   │   ├── network_engineering.json
│   │   ├── automation.json
│   │   ├── electronic_info.json
│   │   ├── iot.json
│   │   ├── computer_science.json
│   │   └── mechanical.json
│   └── questions/       # 题库数据（JSON）
│       ├── quick_assessment.json
│       └── deep_assessment.json
├── models/              # 数据模型
│   ├── schemas.py       # Pydantic 请求/响应模型
│   └── database.py      # SQLAlchemy ORM + 数据库操作
└── templates/           # 预留（报告模板等）
```

## 覆盖专业

- 网络工程 ✅
- 自动化 ✅
- 电子信息工程 ✅
- 物联网工程 ✅
- 计算机科学与技术 ✅
- 机械设计/机电一体化 ✅

## 技术栈

- **后端**: Python 3.11+ / FastAPI
- **前端**: 原生 HTML/CSS/JS（移动端优先 H5）
- **AI**: Claude API (Anthropic) — Sonnet 模型（控成本）
- **数据库**: SQLite（MVP，零配置）/ PostgreSQL（生产）
- **数据模型**: Pydantic v2 + SQLAlchemy 2.0
- **认证**: JWT (python-jose)

## API 文档

启动后访问 http://localhost:8000/docs 查看完整的 Swagger API 文档。

### 核心流程

```
1. GET  /api/assessment/questions/{major}  → 获取题目
2. POST /api/assessment/quick              → 提交自评，获取初步结果
3. POST /api/assessment/deep/start/{id}    → 开始AI深度对话
4. POST /api/assessment/deep/chat          → 对话交互（多轮）
5. POST /api/report/generate/{id}          → 生成完整报告
6. POST /api/report/learning-path/{id}     → 生成学习路径
7. POST /api/interview/start               → 开始面试模拟
8. POST /api/chat/free                     → 自由问答
```
