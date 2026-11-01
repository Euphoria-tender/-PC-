"""
文化DNA —— 非遗作品确权溯源系统
网络发布/同步台账 API 路由
作品发布到网络（IPFS + 离线降级）与台账分页查询。
"""
import os
import time
from flask import Blueprint, request, g, current_app
from sqlalchemy import or_
from app import db
from app.models.artwork import TArtwork
from app.models.publish_record import TPublishRecord
from app.utils.response import success_response, error_response, paginated_response
from app.utils.auth_decorator import token_required, inheritor_required
from app.services.publish_service import publish_work

publish_bp = Blueprint("publish", __name__)


# ── 发布作品到网络 ──────────────────────────────────────────────
@publish_bp.route("/<work_id>", methods=["POST"])
@token_required
@inheritor_required
def publish_work_api(work_id):
    """
    将已提取DNA的作品发布到网络

    流程：
    1. 校验作品存在与权限
    2. 校验DNA已提取（否则无法存证）
    3. 构建元数据快照（含 dna_hash / perceptual_hash / title / images 等）
    4. 发布到 IPFS；不可用时降级为本地离线存证
    5. 写入 t_publish_record 台账并返回

    Path参数: work_id - 作品UUID
    """
    try:
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        if work.user_id != g.current_user["user_id"] and g.current_user.get("role") != "admin":
            return error_response("无权操作该作品", 403)

        # 必须先提取DNA，否则没有可存证的内容
        if not work.fingerprint or work.dna_status != "completed":
            return error_response("请先完成该作品的DNA提取，再进行网络发布", 400)

        # 构建发布内容快照
        metadata = {
            "schema": "cultural-dna/1.0",
            "work_id": work.work_id,
            "title": work.title,
            "category": work.category,
            "description": work.description or "",
            "dna_hash": work.fingerprint.dna_hash,
            "perceptual_hash": work.fingerprint.perceptual_hash or "",
            "images": work.images or [],
            "microscope_images": work.microscope_images or [],
            "owner": work.owner.real_name if work.owner else "",
            "published_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 数据目录（published/ 落在用户数据目录下，与 uploads 同级）
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
        data_dir = os.path.dirname(upload_folder)

        result = publish_work(
            metadata,
            ipfs_host=current_app.config.get("IPFS_HOST", "127.0.0.1"),
            ipfs_port=current_app.config.get("IPFS_PORT", 5001),
            data_dir=data_dir,
        )

        # 写入发布台账
        record = TPublishRecord(
            work_id=work.id,
            publish_type=result["publish_type"],
            cid=result["cid"],
            resource_url=result["resource_url"],
            payload=metadata,
            status="success",
            message=result["message"],
        )
        db.session.add(record)
        db.session.commit()
        db.session.refresh(record)  # 回读 server_default 生成的时间戳

        return success_response({
            "work_id": work.work_id,
            "work_title": work.title,
            "publish_type": record.publish_type,
            "cid": record.cid,
            "resource_url": record.resource_url,
            "status": record.status,
            "message": record.message,
            "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else None,
        }, "发布到网络成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"发布失败: {str(e)}", 500)


# ── 发布台账列表 ────────────────────────────────────────────────
@publish_bp.route("/", methods=["GET"])
@token_required
def list_publish_records():
    """
    分页查询发布/同步台账

    Query参数:
        page:      页码（默认1）
        page_size: 每页条数（默认12）
        keyword:   按作品名/CID 模糊搜索（可选）

    普通用户仅能看到自己作品的发布记录，管理员看全部。
    """
    try:
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 12, type=int)
        keyword = request.args.get("keyword", "").strip()

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 12

        query = TPublishRecord.query.join(
            TArtwork, TPublishRecord.work_id == TArtwork.id
        )

        if g.current_user.get("role") != "admin":
            query = query.filter(TArtwork.user_id == g.current_user["user_id"])

        if keyword:
            query = query.filter(or_(
                TArtwork.title.contains(keyword),
                TPublishRecord.cid.contains(keyword),
            ))

        query = query.order_by(TPublishRecord.created_at.desc())
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        items = []
        for record in pagination.items:
            items.append({
                "id": record.id,
                "work_id": record.artwork.work_id if record.artwork else "",
                "work_title": record.artwork.title if record.artwork else "",
                "publish_type": record.publish_type,
                "cid": record.cid,
                "resource_url": record.resource_url or "",
                "status": record.status,
                "message": record.message or "",
                "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else None,
            })

        return paginated_response(
            items=items,
            total=pagination.total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        return error_response(f"查询发布台账失败: {str(e)}", 500)