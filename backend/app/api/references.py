"""
文化DNA —— 非遗作品确权溯源系统
联网参考图库 API 路由
提供本地图库（联网搜索入库的参考图片）的分页查询。
"""
from flask import Blueprint, request
from sqlalchemy import or_
from app import db
from app.models.reference_image import TReferenceImage
from app.utils.response import success_response, error_response, paginated_response
from app.utils.auth_decorator import token_required

references_bp = Blueprint("references", __name__)


@references_bp.route("/", methods=["GET"])
@token_required
def list_references():
    """
    分页查询本地参考图库（联网搜索入库的参考图片）

    Query参数:
        page:      页码（默认1）
        page_size: 每页条数（默认12，最大100）
        keyword:   按关键词/标题/来源模糊搜索（可选）
    """
    try:
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 12, type=int)
        keyword = request.args.get("keyword", "").strip()

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 12

        query = TReferenceImage.query

        if keyword:
            query = query.filter(or_(
                TReferenceImage.search_query.contains(keyword),
                TReferenceImage.title.contains(keyword),
                TReferenceImage.source.contains(keyword),
            ))

        query = query.order_by(TReferenceImage.created_at.desc())
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        items = []
        for ref in pagination.items:
            items.append({
                "id": ref.id,
                "source": ref.source,
                "query": ref.search_query or "",
                "title": ref.title or "",
                "image_url": ref.image_url or "",
                "source_url": ref.source_url or "",
                "created_at": ref.created_at.strftime("%Y-%m-%d %H:%M:%S") if ref.created_at else None,
            })

        total_references = TReferenceImage.query.count()

        return paginated_response(
            items=items,
            total=pagination.total,
            page=page,
            page_size=page_size,
            extra={"total_references": total_references},
        )

    except Exception as e:
        return error_response(f"查询参考图库失败: {str(e)}", 500)