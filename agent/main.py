"""工科导航 - 技能测评 Agent 服务入口"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import get_settings
from models.database import init_db
from api.assessment import router as assessment_router
from api.report import router as report_router
from api.interview import router as interview_router
from api.chat import router as chat_router
from api.user import router as user_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="工科大学生技能测评与职业发展规划 AI Agent",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由
app.include_router(assessment_router, prefix="/api/assessment", tags=["测评"])
app.include_router(report_router, prefix="/api/report", tags=["报告"])
app.include_router(interview_router, prefix="/api/interview", tags=["面试模拟"])
app.include_router(chat_router, prefix="/api/chat", tags=["AI对话"])
app.include_router(user_router, prefix="/api/user", tags=["用户"])

# 启动时初始化数据库
@app.on_event("startup")
def startup():
    init_db()

# 静态文件 (CSS/JS)
FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def serve_index():
    """首页 → 前端H5页面"""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}
