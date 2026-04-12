"""微信小程序接口

提供微信小程序 web-view 内嵌 H5 所需的后端能力：
1. code2session —— 用 wx.login() 返回的 code 换取 openid
2. 前端 JS 可以通过 URL 参数传入 wx_code，自动关联微信用户

注意：需要在微信小程序管理后台完成以下配置才能正常使用：
- 业务域名：添加您的域名（如 jgzj.org.cn）
- request 合法域名：添加 https://api.weixin.qq.com
"""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import get_settings

router = APIRouter()
settings = get_settings()

WX_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


class WxLoginRequest(BaseModel):
    code: str


class WxLoginResponse(BaseModel):
    openid: str
    session_key: str | None = None  # 不暴露给前端，仅后端使用


@router.post("/code2session", response_model=WxLoginResponse)
async def wx_code2session(req: WxLoginRequest):
    """用小程序 wx.login() 的 code 换取 openid

    流程：
    1. 小程序调用 wx.login() → 拿到 code
    2. 小程序把 code 通过 URL 参数传给 web-view 内的 H5
    3. H5 的 JS 读到 wx_code 参数后调用本接口
    4. 本接口向微信服务器换取 openid
    5. 返回 openid 给前端，前端存储后续请求带上
    """
    if not settings.wechat_app_id or not settings.wechat_app_secret:
        raise HTTPException(
            status_code=503,
            detail="微信小程序未配置（请在 .env 中设置 WECHAT_APP_ID 和 WECHAT_APP_SECRET）",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(WX_CODE2SESSION_URL, params={
                "appid": settings.wechat_app_id,
                "secret": settings.wechat_app_secret,
                "js_code": req.code,
                "grant_type": "authorization_code",
            })
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"请求微信服务器失败: {e}")

    if "errcode" in data and data["errcode"] != 0:
        raise HTTPException(
            status_code=400,
            detail=f"微信登录失败: {data.get('errmsg', '未知错误')} (errcode={data.get('errcode')})",
        )

    openid = data.get("openid")
    if not openid:
        raise HTTPException(status_code=400, detail="未获取到 openid")

    return WxLoginResponse(openid=openid)


@router.get("/config")
async def wx_config():
    """返回前端需要的微信配置（仅返回 appId，不返回 secret）"""
    return {
        "app_id": settings.wechat_app_id,
        "configured": bool(settings.wechat_app_id and settings.wechat_app_secret),
    }
