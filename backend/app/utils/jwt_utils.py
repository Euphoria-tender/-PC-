"""
文化DNA —— 非遗作品确权溯源系统
JWT 令牌工具模块
"""
import jwt
from datetime import datetime, timedelta
from flask import current_app, request
from typing import Optional, Dict, Any


def generate_token(user_id: int, role: str, token_type: str = "access") -> str:
    """
    生成JWT令牌

    Args:
        user_id: 用户ID
        role: 用户角色
        token_type: 令牌类型（access / refresh）

    Returns:
        JWT令牌字符串
    """
    if token_type == "access":
        expires = datetime.utcnow() + current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    else:
        expires = datetime.utcnow() + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]

    payload = {
        "user_id": user_id,
        "role": role,
        "type": token_type,
        "exp": expires,
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256"
    )
    return token


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码并验证JWT令牌

    Args:
        token: JWT令牌字符串

    Returns:
        解码后的payload字典，验证失败返回None
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user_id() -> Optional[int]:
    """
    从请求头中获取当前登录用户ID

    Returns:
        用户ID，未登录或令牌无效时返回None
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split("Bearer ")[1]
    payload = decode_token(token)
    if payload is None:
        return None
    return payload.get("user_id")


def get_current_user_role() -> Optional[str]:
    """
    从请求头中获取当前登录用户角色

    Returns:
        用户角色，未登录或令牌无效时返回None
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split("Bearer ")[1]
    payload = decode_token(token)
    if payload is None:
        return None
    return payload.get("role")