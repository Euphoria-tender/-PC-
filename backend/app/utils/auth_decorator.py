"""
文化DNA —— 非遗作品确权溯源系统
JWT 认证装饰器模块
提供 @token_required 装饰器，用于保护需要登录的API端点
"""
from functools import wraps
from flask import request, g
from app.utils.jwt_utils import decode_token
from app.utils.response import error_response


def token_required(f):
    """
    JWT 认证装饰器

    验证请求头 Authorization: Bearer <token>
    验证通过后将 payload 写入 flask.g.current_user
    验证失败返回 401

    使用方式:
        @auth_bp.route("/profile")
        @token_required
        def profile():
            user_id = g.current_user["user_id"]
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # 从请求头提取 Bearer Token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1]

        if not token:
            return error_response("未提供认证令牌，请先登录", 401)

        # 解码并验证令牌
        payload = decode_token(token)
        if payload is None:
            return error_response("认证令牌无效或已过期，请重新登录", 401)

        # 将当前用户信息注入请求上下文
        g.current_user = {
            "user_id": payload.get("user_id"),
            "role": payload.get("role"),
        }
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """
    管理员权限装饰器（需配合 @token_required 使用）

    使用方式:
        @auth_bp.route("/admin-only")
        @token_required
        @admin_required
        def admin_only():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if g.current_user.get("role") != "admin":
            return error_response("权限不足，仅管理员可访问", 403)
        return f(*args, **kwargs)

    return decorated


def inheritor_required(f):
    """
    传承人权限装饰器（需配合 @token_required 使用）
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        role = g.current_user.get("role")
        if role not in ("inheritor", "admin"):
            return error_response("权限不足，仅传承人或管理员可操作", 403)
        return f(*args, **kwargs)

    return decorated


def reviewer_required(f):
    """
    审核专家权限装饰器（鉴定师或管理员，需配合 @token_required 使用）
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        role = g.current_user.get("role")
        if role not in ("appraiser", "admin"):
            return error_response("权限不足，仅鉴定师或管理员可审核", 403)
        return f(*args, **kwargs)

    return decorated