"""
文化DNA —— 身份认证申请模块 API 路由
普通用户提交资料申请认证为传承人/鉴定师；管理员审核通过后自动变更其角色。
"""
from datetime import datetime

from flask import Blueprint, request, g
from app import db
from app.models.user import TUser
from app.models.role_application import TRoleApplication
from app.utils.response import success_response, error_response, paginated_response
from app.utils.auth_decorator import token_required, admin_required

certification_bp = Blueprint("certification", __name__)

# 可自助申请的目标身份（管理员不可自助申请）
VALID_TARGET_ROLES = ("inheritor", "appraiser")


def _serialize(app_obj):
    """序列化申请记录"""
    return {
        "id": app_obj.id,
        "target_role": app_obj.target_role,
        "real_name": app_obj.real_name,
        "phone": app_obj.phone or "",
        "materials": app_obj.materials,
        "status": app_obj.status,
        "review_comment": app_obj.review_comment or "",
        "reviewer_name": app_obj.reviewer.real_name if app_obj.reviewer else "",
        "applicant_username": app_obj.applicant.username if app_obj.applicant else "",
        "created_at": app_obj.created_at.strftime("%Y-%m-%d %H:%M:%S") if app_obj.created_at else None,
        "reviewed_at": app_obj.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if app_obj.reviewed_at else None,
    }


# ── 提交认证申请 ────────────────────────────────────────────────
@certification_bp.route("/", methods=["POST"])
@token_required
def apply_role():
    """
    提交身份认证申请

    请求体: {
        "target_role": "inheritor" | "appraiser",
        "real_name": "真实姓名",
        "phone": "联系电话（选填）",
        "materials": "申请资料说明"
    }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        target_role = data.get("target_role", "").strip()
        real_name = data.get("real_name", "").strip()
        phone = data.get("phone", "").strip()
        materials = data.get("materials", "").strip()

        if target_role not in VALID_TARGET_ROLES:
            return error_response("无效的目标身份，仅可选择传承人或鉴定师", 400)
        if not real_name:
            return error_response("真实姓名不能为空", 400)
        if not materials or len(materials) < 10:
            return error_response("请填写不少于10字的申请资料说明", 400)

        current = db.session.get(TUser, g.current_user["user_id"])
        if not current:
            return error_response("用户不存在", 404)
        if current.role == "admin":
            return error_response("管理员无需申请身份认证", 400)
        if current.role == target_role:
            return error_response("您已是该身份，无需重复申请", 400)

        existing = TRoleApplication.query.filter_by(
            user_id=current.id, target_role=target_role, status="pending"
        ).first()
        if existing:
            return error_response("您已提交过该身份的认证申请，等待审核中", 409)

        application = TRoleApplication(
            user_id=current.id,
            target_role=target_role,
            real_name=real_name,
            phone=phone or None,
            materials=materials,
            status="pending",
        )
        db.session.add(application)
        db.session.commit()

        return success_response(_serialize(application), "认证申请已提交，请等待管理员审核")

    except Exception as e:
        db.session.rollback()
        return error_response(f"提交认证申请失败: {str(e)}", 500)


# ── 我的申请记录 ────────────────────────────────────────────────
@certification_bp.route("/mine", methods=["GET"])
@token_required
def my_applications():
    """查询当前用户的认证申请记录（按提交时间倒序）"""
    try:
        apps = TRoleApplication.query.filter_by(
            user_id=g.current_user["user_id"]
        ).order_by(TRoleApplication.id.desc()).all()

        return success_response({"items": [_serialize(a) for a in apps]})
    except Exception as e:
        return error_response(f"查询申请记录失败: {str(e)}", 500)


# ── 管理员：申请列表 ────────────────────────────────────────────
@certification_bp.route("/", methods=["GET"])
@token_required
@admin_required
def list_applications():
    """
    管理员分页查询认证申请

    Query参数: page / page_size / status / keyword
    """
    try:
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)
        status = request.args.get("status", "").strip()
        keyword = request.args.get("keyword", "").strip()

        query = TRoleApplication.query

        if status in ("pending", "approved", "rejected"):
            query = query.filter_by(status=status)
        if keyword:
            query = query.filter(
                db.or_(
                    TRoleApplication.real_name.like(f"%{keyword}%"),
                    TRoleApplication.phone.like(f"%{keyword}%"),
                )
            )

        pagination = query.order_by(TRoleApplication.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return paginated_response(
            items=[_serialize(a) for a in pagination.items],
            total=pagination.total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        return error_response(f"获取认证申请列表失败: {str(e)}", 500)


# ── 管理员：审核申请 ────────────────────────────────────────────
@certification_bp.route("/<int:app_id>", methods=["PUT"])
@token_required
@admin_required
def review_application(app_id):
    """
    审核身份认证申请（通过/驳回）

    请求体: {
        "status": "approved" | "rejected",
        "review_comment": "审核意见"
    }
    通过后自动将申请人角色变更为其申请的目标身份，并同步更新姓名/电话。
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        status = data.get("status", "").strip()
        comment = data.get("review_comment", "").strip()

        if status not in ("approved", "rejected"):
            return error_response("审核状态无效，应为 approved 或 rejected", 400)
        if status == "rejected" and not comment:
            return error_response("驳回时必须填写审核意见", 400)

        application = db.session.get(TRoleApplication, app_id)
        if not application:
            return error_response("申请不存在", 404)
        if application.status != "pending":
            return error_response("该申请已处理，不能重复审核", 400)

        if status == "approved":
            user = db.session.get(TUser, application.user_id)
            if not user:
                return error_response("申请人不存在", 404)
            user.role = application.target_role
            user.real_name = application.real_name
            if application.phone:
                user.phone = application.phone

        application.status = status
        application.review_comment = comment or None
        application.reviewed_by = g.current_user["user_id"]
        application.reviewed_at = datetime.utcnow()
        db.session.commit()

        return success_response(_serialize(application), "审核完成")

    except Exception as e:
        db.session.rollback()
        return error_response(f"审核失败: {str(e)}", 500)