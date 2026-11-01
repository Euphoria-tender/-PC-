"""
文化DNA —— 非遗作品确权溯源系统
作品管理模块 API 路由
实现作品CRUD、图片上传、DNA提取触发
"""
import os
import uuid
import time
from flask import Blueprint, request, g, current_app
from werkzeug.utils import secure_filename
from app import db
from app.models.artwork import TArtwork
from app.models.fingerprint import TFingerprint
from app.utils.response import success_response, error_response, paginated_response
from app.utils.auth_decorator import token_required, inheritor_required
from app.services.ai_service import extract_dna_features

works_bp = Blueprint("works", __name__)

# 作品类别（与前端 src/constants.ts 的 CATEGORIES 保持一致，避免新增类别被后端拒绝）
VALID_CATEGORIES = (
    "刺绣", "陶瓷", "木雕", "剪纸", "漆器",
    "紫砂", "景泰蓝", "竹编", "石雕", "青铜器", "其他",
)


def _allowed_image(filename: str) -> bool:
    """检查文件扩展名是否在允许的图片类型中"""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", set())


def _save_uploaded_image(file) -> str:
    """
    保存上传的图片文件到本地

    Args:
        file: Flask FileStorage 对象

    Returns:
        保存后的相对路径
    """
    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
    # 按日期分目录存储
    date_dir = time.strftime("%Y%m")
    target_dir = os.path.join(upload_folder, date_dir)
    os.makedirs(target_dir, exist_ok=True)

    # 生成唯一文件名
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(target_dir, filename)
    file.save(filepath)

    # 返回相对路径（前端拼接完整URL）
    return f"/{date_dir}/{filename}"


# ── 作品列表查询 ────────────────────────────────────────────────
@works_bp.route("/", methods=["GET"])
@token_required
def list_works():
    """
    分页查询作品列表，支持按类别、状态筛选

    Query参数:
        page:     页码（默认1）
        page_size: 每页条数（默认12，最大100）
        category:  按类别筛选（可选）
        dna_status: 按DNA状态筛选（可选）
        keyword:   按标题模糊搜索（可选）
    """
    try:
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 12, type=int)
        category = request.args.get("category", "").strip()
        dna_status = request.args.get("dna_status", "").strip()
        keyword = request.args.get("keyword", "").strip()

        # 参数校验
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 12

        # 构建查询
        query = TArtwork.query

        # 普通用户只能看自己的作品，管理员可看全部
        if g.current_user.get("role") != "admin":
            query = query.filter_by(user_id=g.current_user["user_id"])

        if category:
            query = query.filter_by(category=category)
        if dna_status:
            query = query.filter_by(dna_status=dna_status)
        if keyword:
            query = query.filter(TArtwork.title.contains(keyword))

        # 按更新时间倒序
        query = query.order_by(TArtwork.updated_at.desc())

        # 分页
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        items = pagination.items

        # 序列化
        works_list = []
        for work in items:
            works_list.append({
                "id": work.id,
                "work_id": work.work_id,
                "title": work.title,
                "category": work.category,
                "description": work.description,
                "images": work.images or [],
                "dna_status": work.dna_status,
                "created_at": work.created_at.strftime("%Y-%m-%d %H:%M:%S") if work.created_at else None,
                "updated_at": work.updated_at.strftime("%Y-%m-%d %H:%M:%S") if work.updated_at else None,
                "owner_name": work.owner.real_name if work.owner else "",
            })

        return paginated_response(
            items=works_list,
            total=pagination.total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        return error_response(f"查询作品列表失败: {str(e)}", 500)


# ── 作品详情 ────────────────────────────────────────────────────
@works_bp.route("/<work_id>", methods=["GET"])
@token_required
def get_work(work_id):
    """
    根据作品编号获取详情

    Path参数: work_id - 作品UUID
    """
    try:
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        # 权限检查：非管理员只能看自己的作品
        if g.current_user.get("role") != "admin" and work.user_id != g.current_user["user_id"]:
            return error_response("无权查看该作品", 403)

        # 构建详情
        work_detail = {
            "id": work.id,
            "work_id": work.work_id,
            "title": work.title,
            "category": work.category,
            "description": work.description,
            "images": work.images or [],
            "microscope_images": work.microscope_images or [],
            "dna_status": work.dna_status,
            "created_at": work.created_at.strftime("%Y-%m-%d %H:%M:%S") if work.created_at else None,
            "updated_at": work.updated_at.strftime("%Y-%m-%d %H:%M:%S") if work.updated_at else None,
            "owner": {
                "id": work.owner.id,
                "real_name": work.owner.real_name,
                "role": work.owner.role,
            } if work.owner else None,
            "fingerprint": {
                "dna_hash": work.fingerprint.dna_hash,
                "extracted_at": work.fingerprint.extracted_at.strftime("%Y-%m-%d %H:%M:%S") if work.fingerprint and work.fingerprint.extracted_at else None,
            } if work.fingerprint else None,
            "chain_records": [
                {
                    "certificate_no": cr.certificate_no,
                    "tx_id": cr.tx_id,
                    "block_height": cr.block_height,
                    "status": cr.status,
                    "created_at": cr.created_at.strftime("%Y-%m-%d %H:%M:%S") if cr.created_at else None,
                }
                for cr in work.chain_records.order_by(TArtwork.chain_records.property.mapper.class_.created_at.desc()).limit(5).all()
            ] if work.chain_records else [],
        }

        return success_response(work_detail)

    except Exception as e:
        return error_response(f"查询作品详情失败: {str(e)}", 500)


# ── 创建作品 ────────────────────────────────────────────────────
@works_bp.route("/", methods=["POST"])
@token_required
@inheritor_required
def create_work():
    """
    创建新作品（支持上传图片）

    表单字段:
        title:        作品名称（必填）
        category:     作品类别（必填）
        description:  作品描述（可选）
        images:       作品图片文件（可多选，最多5张）
    """
    try:
        # 从表单获取文本字段
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        # 参数校验
        if not title:
            return error_response("作品名称不能为空", 400)
        if not category:
            return error_response("作品类别不能为空", 400)

        valid_categories = VALID_CATEGORIES
        if category not in valid_categories:
            return error_response(f"无效的作品类别，允许: {', '.join(valid_categories)}", 400)

        # 处理图片上传
        image_urls = []
        uploaded_files = request.files.getlist("images")
        if uploaded_files:
            if len(uploaded_files) > 5:
                return error_response("最多上传5张图片", 400)

            for file in uploaded_files:
                if file.filename == "":
                    continue
                if not _allowed_image(file.filename):
                    return error_response(f"不支持的图片格式: {file.filename}", 400)
                try:
                    saved_path = _save_uploaded_image(file)
                    image_urls.append(saved_path)
                except Exception as e:
                    return error_response(f"图片保存失败: {str(e)}", 500)

        # 创建作品
        new_work = TArtwork(
            work_id=str(uuid.uuid4()),
            user_id=g.current_user["user_id"],
            title=title,
            category=category,
            description=description,
            images=image_urls if image_urls else None,
            dna_status="pending",
        )
        db.session.add(new_work)
        db.session.commit()

        return success_response({
            "work_id": new_work.work_id,
            "title": new_work.title,
            "category": new_work.category,
            "images": new_work.images or [],
            "dna_status": new_work.dna_status,
        }, "作品创建成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"创建作品失败: {str(e)}", 500)


# ── 更新作品 ────────────────────────────────────────────────────
@works_bp.route("/<work_id>", methods=["PUT"])
@token_required
@inheritor_required
def update_work(work_id):
    """
    更新作品信息

    请求体: { "title": "xxx", "category": "xxx", "description": "xxx" }
    """
    try:
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        # 权限检查
        if work.user_id != g.current_user["user_id"] and g.current_user.get("role") != "admin":
            return error_response("无权修改该作品", 403)

        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        # 更新可修改字段
        if "title" in data:
            new_title = data["title"].strip()
            if not new_title:
                return error_response("作品名称不能为空", 400)
            work.title = new_title

        if "category" in data:
            new_category = data["category"].strip()
            valid_categories = VALID_CATEGORIES
            if new_category not in valid_categories:
                return error_response(f"无效的作品类别，允许: {', '.join(valid_categories)}", 400)
            work.category = new_category

        if "description" in data:
            work.description = data["description"].strip()

        db.session.commit()

        return success_response({
            "work_id": work.work_id,
            "title": work.title,
            "category": work.category,
            "description": work.description,
        }, "作品更新成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"更新作品失败: {str(e)}", 500)


# ── 删除作品 ────────────────────────────────────────────────────
@works_bp.route("/<work_id>", methods=["DELETE"])
@token_required
@inheritor_required
def delete_work(work_id):
    """
    删除作品（物理删除，级联删除关联指纹、存证、转让、鉴定记录）
    """
    try:
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        # 权限检查
        if work.user_id != g.current_user["user_id"] and g.current_user.get("role") != "admin":
            return error_response("无权删除该作品", 403)

        db.session.delete(work)
        db.session.commit()

        return success_response(message="作品已删除")

    except Exception as e:
        db.session.rollback()
        return error_response(f"删除作品失败: {str(e)}", 500)


# ── 提取DNA指纹 ─────────────────────────────────────────────────
@works_bp.route("/<work_id>/extract-dna", methods=["POST"])
@token_required
@inheritor_required
def extract_dna(work_id):
    """
    触发AI特征提取，生成作品DNA指纹

    要求作品已上传images和microscope_images
    """
    try:
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        if work.user_id != g.current_user["user_id"] and g.current_user.get("role") != "admin":
            return error_response("无权操作该作品", 403)

        if not work.images:
            return error_response("请先上传作品图片", 400)
        if not work.microscope_images:
            return error_response("请先上传微观图像", 400)

        if work.dna_status == "processing":
            return error_response("DNA提取正在进行中，请稍后再试", 409)

        # 更新状态为处理中
        work.dna_status = "processing"
        db.session.commit()

        try:
            # 调用AI服务提取特征向量
            upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
            image_paths = [os.path.join(upload_folder, img.lstrip("/")) for img in work.images]
            microscope_paths = [os.path.join(upload_folder, img.lstrip("/")) for img in work.microscope_images]

            result = extract_dna_features(image_paths, microscope_paths)

            if result is None:
                work.dna_status = "failed"
                db.session.commit()
                return error_response("DNA特征提取失败，请检查图片质量", 500)

            dna_hash, feature_tensor, perceptual_hash = result

            # 保存指纹记录（先删旧记录再创建新记录）
            if work.fingerprint:
                db.session.delete(work.fingerprint)

            fingerprint = TFingerprint(
                work_id=work.id,
                dna_hash=dna_hash,
                feature_vector=feature_tensor,
                perceptual_hash=perceptual_hash,
            )
            db.session.add(fingerprint)
            work.dna_status = "completed"
            db.session.commit()

            return success_response({
                "work_id": work.work_id,
                "dna_hash": dna_hash,
                "dna_status": "completed",
            }, "DNA指纹提取成功")

        except Exception as e:
            work.dna_status = "failed"
            db.session.commit()
            return error_response(f"DNA提取过程异常: {str(e)}", 500)

    except Exception as e:
        db.session.rollback()
        return error_response(f"DNA提取请求失败: {str(e)}", 500)


# ── 上传微观图像 ────────────────────────────────────────────────
@works_bp.route("/<work_id>/upload-micro", methods=["POST"])
@token_required
@inheritor_required
def upload_microscope(work_id):
    """
    上传微观扫描图像

    表单字段: microscope_images - 显微图像文件（可多选，最多5张）
    """
    try:
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        if work.user_id != g.current_user["user_id"] and g.current_user.get("role") != "admin":
            return error_response("无权操作该作品", 403)

        uploaded_files = request.files.getlist("microscope_images")
        if not uploaded_files or all(f.filename == "" for f in uploaded_files):
            return error_response("请选择要上传的显微图像", 400)

        if len(uploaded_files) > 5:
            return error_response("最多上传5张显微图像", 400)

        image_urls = list(work.microscope_images) if work.microscope_images else []

        for file in uploaded_files:
            if file.filename == "":
                continue
            if not _allowed_image(file.filename):
                return error_response(f"不支持的图片格式: {file.filename}", 400)
            try:
                saved_path = _save_uploaded_image(file)
                image_urls.append(saved_path)
            except Exception as e:
                return error_response(f"图片保存失败: {str(e)}", 500)

        work.microscope_images = image_urls
        db.session.commit()

        return success_response({
            "work_id": work.work_id,
            "microscope_images": image_urls,
            "count": len(image_urls),
        }, "显微图像上传成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"上传显微图像失败: {str(e)}", 500)