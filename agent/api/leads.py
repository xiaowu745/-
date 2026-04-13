"""私域线索收集 API

提供两组端点：
1. 用户侧：POST /api/leads/submit —— 用户在看报告前弹窗提交手机号
2. 管理侧：POST /api/leads/admin/login      —— 凭密码换 token
              GET  /api/leads/admin/list       —— 查看线索列表
              PATCH /api/leads/admin/{lead_id}  —— 更新跟进状态/备注
              GET  /api/leads/admin/export.csv —— 导出 CSV

新线索提交成功后，如果配置了企业微信 webhook，会异步推送通知。
"""

import base64
import csv
import hashlib
import hmac
import io
import json
import re
import time
from datetime import datetime

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import get_settings
from models.database import (
    Lead,
    get_db,
    iter_leads_for_export,
    list_leads,
    update_lead,
    upsert_lead,
)
from models.database import AssessmentRecord

router = APIRouter()
settings = get_settings()

# 中国大陆手机号：1 开头 + 10 位数字
_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


# ============ 工具函数 ============

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _create_admin_token() -> str:
    """生成一个简单的管理员 token（HS256 签名），有效期 12 小时"""
    expire = int(time.time()) + 12 * 3600
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({"role": "admin", "exp": expire}).encode())
    msg = f"{header}.{payload}"
    sig = hmac.new(settings.secret_key.encode(), msg.encode(), hashlib.sha256).digest()
    return f"{msg}.{_b64(sig)}"


def _verify_admin_token(token: str) -> bool:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False
        header_b64, payload_b64, sig_b64 = parts
        msg = f"{header_b64}.{payload_b64}"
        expected_sig = _b64(
            hmac.new(settings.secret_key.encode(), msg.encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(expected_sig, sig_b64):
            return False
        # 解码 payload 检查过期
        pad = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64 + pad).decode()
        payload = json.loads(payload_json)
        if payload.get("role") != "admin":
            return False
        if int(payload.get("exp", 0)) < int(time.time()):
            return False
        return True
    except Exception:
        return False


def _require_admin(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    token = authorization.split(" ", 1)[1].strip()
    if not _verify_admin_token(token):
        raise HTTPException(status_code=401, detail="token 无效或已过期")


async def _notify_wecom(lead: dict):
    """向企业微信群机器人推送新线索通知（失败不影响主流程）"""
    if not settings.lead_notify_enabled:
        return
    webhook = settings.wecom_webhook_url
    if not webhook:
        return

    weak = lead.get("weak_dimensions") or []
    weak_str = "、".join(weak) if isinstance(weak, list) else str(weak)
    content = (
        f"🔔 新线索留资\n"
        f"────────────\n"
        f"手机号：{lead.get('phone', '')}\n"
        f"昵称：{lead.get('nickname') or '-'}\n"
        f"专业：{lead.get('major') or '-'}\n"
        f"年级：{lead.get('grade') or '-'}\n"
        f"学校：{lead.get('school_tier') or '-'}\n"
        f"综合分：{lead.get('overall_score') if lead.get('overall_score') is not None else '-'}\n"
        f"薄弱项：{weak_str or '-'}\n"
        f"来源：{lead.get('source') or '-'}\n"
        f"时间：{lead.get('created_at') or '-'}"
    )
    payload = {"msgtype": "text", "text": {"content": content}}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(webhook, json=payload)
    except Exception as e:
        # 推送失败只记录日志，不影响用户流程
        print(f"[WeCom] webhook push failed: {e}")


def _get_assessment_snapshot(session_id: str | None) -> dict:
    """从测评记录中拉一份学生信息 + 得分快照，用于冗余到 Lead 表"""
    if not session_id:
        return {}
    db = get_db()
    try:
        record = db.query(AssessmentRecord).filter_by(session_id=session_id).first()
        if not record:
            return {}
        return {
            "nickname": record.nickname,
            "major": record.major,
            "grade": record.grade,
            "school_tier": record.school_tier,
            "overall_score": record.overall_score,
            "weak_dimensions": record.weak_dimensions,
        }
    finally:
        db.close()


# ============ 请求/响应 模型 ============

class LeadSubmitRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11)
    consent: bool = Field(..., description="是否勾选隐私同意")
    session_id: str | None = None
    source: str = "report_gate"
    # 如果前端有上下文信息可以一起传
    nickname: str | None = None
    major: str | None = None
    grade: str | None = None
    school_tier: str | None = None
    overall_score: int | None = None
    weak_dimensions: list | None = None


class AdminLoginRequest(BaseModel):
    password: str


# ============ 用户侧端点 ============

@router.post("/submit")
async def submit_lead(req: LeadSubmitRequest, request: Request):
    """用户提交手机号留资（看报告前弹窗）"""
    if not _PHONE_RE.match(req.phone):
        raise HTTPException(status_code=400, detail="请输入正确的 11 位手机号")
    if not req.consent:
        raise HTTPException(status_code=400, detail="请先勾选同意隐私条款")

    # 优先用前端传入的信息，缺失的从数据库测评记录中补齐
    snapshot = _get_assessment_snapshot(req.session_id)
    data = {
        "phone": req.phone,
        "session_id": req.session_id,
        "source": req.source or "report_gate",
        "consent": True,
        "nickname": req.nickname or snapshot.get("nickname"),
        "major": req.major or snapshot.get("major"),
        "grade": req.grade or snapshot.get("grade"),
        "school_tier": req.school_tier or snapshot.get("school_tier"),
        "overall_score": req.overall_score if req.overall_score is not None else snapshot.get("overall_score"),
        "weak_dimensions": req.weak_dimensions if req.weak_dimensions is not None else snapshot.get("weak_dimensions"),
        "ip": request.client.host if request.client else None,
        "user_agent": (request.headers.get("user-agent") or "")[:255],
    }

    lead = upsert_lead(data)

    # 只有新线索才推送企微通知，避免重复提交刷屏
    if lead.get("is_new"):
        try:
            await _notify_wecom(lead)
        except Exception:
            pass

    return {"ok": True, "is_new": lead.get("is_new", False)}


# ============ 管理侧端点 ============

@router.post("/admin/login")
async def admin_login(req: AdminLoginRequest):
    """管理员登录（凭密码换 token）"""
    # 用 bytes 比较，避免密码含中文等非 ASCII 字符时 compare_digest 报 TypeError
    provided = (req.password or "").encode("utf-8")
    expected = (settings.admin_password or "").encode("utf-8")
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="密码错误")
    token = _create_admin_token()
    return {"token": token, "expires_in": 12 * 3600}


@router.get("/admin/list")
async def admin_list(
    authorization: str | None = Header(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    major: str | None = None,
    grade: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
):
    """分页查询线索列表"""
    _require_admin(authorization)
    return list_leads(
        limit=limit,
        offset=offset,
        major=major,
        grade=grade,
        status=status,
        keyword=keyword,
    )


class AdminUpdateRequest(BaseModel):
    status: str | None = None
    notes: str | None = None


@router.patch("/admin/{lead_id}")
async def admin_update(
    lead_id: int,
    req: AdminUpdateRequest,
    authorization: str | None = Header(None),
):
    """更新销售跟进状态或备注"""
    _require_admin(authorization)
    lead = update_lead(lead_id, status=req.status, notes=req.notes)
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    return lead


@router.get("/admin/export.csv")
async def admin_export(authorization: str | None = Header(None)):
    """以 CSV 格式导出全部线索（流式输出）"""
    _require_admin(authorization)

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        # UTF-8 BOM，让 Excel 中文不乱码
        yield "\ufeff"
        headers = [
            "id", "手机号", "昵称", "专业", "年级", "学校层次",
            "综合分", "薄弱项", "来源", "状态", "备注",
            "session_id", "IP", "创建时间",
        ]
        writer.writerow(headers)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        for lead in iter_leads_for_export():
            weak = lead.get("weak_dimensions")
            weak_str = "、".join(weak) if isinstance(weak, list) else (weak or "")
            writer.writerow([
                lead.get("id"),
                lead.get("phone"),
                lead.get("nickname") or "",
                lead.get("major") or "",
                lead.get("grade") or "",
                lead.get("school_tier") or "",
                lead.get("overall_score") if lead.get("overall_score") is not None else "",
                weak_str,
                lead.get("source") or "",
                lead.get("status") or "",
                lead.get("notes") or "",
                lead.get("session_id") or "",
                lead.get("ip") or "",
                lead.get("created_at") or "",
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    filename = f"leads-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        generate(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
