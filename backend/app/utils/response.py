"""
文化DNA —— 非遗作品确权溯源系统
统一响应封装工具
"""
from flask import jsonify
from typing import Any, Optional


def success_response(data: Any = None, message: str = "success") -> tuple:
    """
    成功响应封装

    Args:
        data: 返回数据
        message: 提示信息

    Returns:
        (Flask Response, HTTP 200)
    """
    return jsonify({
        "code": 0,
        "message": message,
        "data": data if data is not None else {}
    }), 200


def error_response(message: str = "error", code: int = 400, data: Optional[Any] = None) -> tuple:
    """
    错误响应封装

    Args:
        message: 错误提示信息
        code: 业务错误码
        data: 附加数据（可选）

    Returns:
        (Flask Response, HTTP status code)
    """
    return jsonify({
        "code": code,
        "message": message,
        "data": data if data is not None else {}
    }), code


def paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "success",
    extra: Optional[dict] = None
) -> tuple:
    """
    分页响应封装

    Args:
        items: 当前页数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页条数
        message: 提示信息
        extra: 附加字段（可选，合并进 data，如 total_admins）

    Returns:
        (Flask Response, HTTP 200)
    """
    data = {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        }
    }
    if extra:
        data.update(extra)
    return jsonify({
        "code": 0,
        "message": message,
        "data": data
    }), 200