"""
文化DNA —— 管理员模块 API 路由
用户管理、作品审核、数据仪表盘（admin-only）
"""
import bcrypt
from flask import Blueprint, request, g
from app import db
from app.models.user import TUser
from app.models.artwork import TArtwork
from app.models.fingerprint import TFingerprint
from app.models.chain_record import TChainRecord
from app.models.verification_log import TVerificationLog
from app.utils.response import success_response, error_response, paginated_response
from app.utils.auth_decorator import token_required, admin_required, reviewer_required
from datetime import datetime

admin_bp = Blueprint("admin", __name__)


def _last_admin() -> bool:
    """系统当前是否只剩一个管理员账号"""
    return TUser.query.filter_by(role="admin").count() <= 1


# 专家评级档位（与前端 constants.ts GRADE_OPTIONS 保持一致）
_VALID_GRADES = ("master", "premium", "excellent", "qualified")


# ═══════════════════════════════════════════════════════════════
# 用户管理
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/users", methods=["GET"])
@token_required
@admin_required
def list_users():
    """
    获取用户列表（分页 + 搜索 + 角色筛选）

    Query参数:
        page: 页码（默认1）
        page_size: 每页数量（默认20）
        keyword: 搜索关键词（用户名/真实姓名）
        role: 角色筛选
    """
    try:
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)
        keyword = request.args.get("keyword", "").strip()
        role = request.args.get("role", "").strip()

        query = TUser.query

        if keyword:
            query = query.filter(
                db.or_(
                    TUser.username.like(f"%{keyword}%"),
                    TUser.real_name.like(f"%{keyword}%"),
                )
            )

        if role and role in ("admin", "inheritor", "appraiser", "user"):
            query = query.filter_by(role=role)

        pagination = query.order_by(TUser.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        users = []
        for u in pagination.items:
            users.append({
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "real_name": u.real_name,
                "phone": u.phone or "",
                "openid": u.openid or "",
                "must_change_password": u.must_change_password,
                "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else None,
            })

        return paginated_response(
            items=users,
            total=pagination.total,
            page=page,
            page_size=page_size,
            extra={"total_admins": TUser.query.filter_by(role="admin").count()},
        )

    except Exception as e:
        return error_response(f"获取用户列表失败: {str(e)}", 500)


@admin_bp.route("/users", methods=["POST"])
@token_required
@admin_required
def create_user():
    """
    创建用户（管理员）

    请求体: {
        "username": "xxx",
        "password": "xxx",
        "real_name": "xxx",
        "phone": "xxx",
        "role": "admin|inheritor|appraiser|user"
    }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        real_name = data.get("real_name", "").strip()
        phone = data.get("phone", "").strip()
        role = data.get("role", "user").strip()

        if not username or len(username) < 3:
            return error_response("用户名至少需要3个字符", 400)
        if not password or len(password) < 6:
            return error_response("密码至少需要6个字符", 400)
        if not real_name:
            return error_response("真实姓名不能为空", 400)

        allowed_roles = ("admin", "inheritor", "appraiser", "user")
        if role not in allowed_roles:
            return error_response(f"无效的角色: {role}", 400)

        existing = TUser.query.filter_by(username=username).first()
        if existing:
            return error_response("用户名已被注册", 409)

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        user = TUser(
            username=username,
            password_hash=password_hash,
            role=role,
            real_name=real_name,
            phone=phone,
            must_change_password=True,
        )
        db.session.add(user)
        db.session.commit()

        return success_response({
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "real_name": user.real_name,
        }, "用户创建成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"创建用户失败: {str(e)}", 500)


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@token_required
@admin_required
def update_user(user_id):
    """
    编辑用户信息（管理员）

    请求体: {
        "real_name": "xxx",
        "phone": "xxx",
        "role": "xxx"
    }
    """
    try:
        user = db.session.get(TUser, user_id)
        if not user:
            return error_response("用户不存在", 404)

        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        if "real_name" in data:
            user.real_name = data["real_name"].strip()
        if "phone" in data:
            user.phone = data["phone"].strip()
        if "role" in data:
            role = data["role"].strip()
            if role not in ("admin", "inheritor", "appraiser", "user"):
                return error_response(f"无效的角色: {role}", 400)
            # 不允许把最后一个管理员降级为其他角色
            if user.role == "admin" and role != "admin" and _last_admin():
                return error_response("系统至少保留一个管理员账号，不能变更其角色", 400)
            user.role = role

        db.session.commit()

        return success_response({
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "real_name": user.real_name,
            "phone": user.phone,
        }, "用户信息更新成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"更新用户失败: {str(e)}", 500)


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@token_required
@admin_required
def delete_user(user_id):
    """删除用户（管理员，不能删除自己）"""
    try:
        current_user_id = g.current_user["user_id"]
        if user_id == current_user_id:
            return error_response("不能删除自己的账号", 400)

        user = db.session.get(TUser, user_id)
        if not user:
            return error_response("用户不存在", 404)

        # 系统始终至少保留一个管理员
        if user.role == "admin" and _last_admin():
            return error_response("系统至少保留一个管理员账号，不能删除", 400)

        db.session.delete(user)
        db.session.commit()

        return success_response(message="用户已删除")

    except Exception as e:
        db.session.rollback()
        return error_response(f"删除用户失败: {str(e)}", 500)


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["PUT"])
@token_required
@admin_required
def reset_user_password(user_id):
    """重置用户密码（管理员）"""
    try:
        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        new_password = data.get("new_password", "").strip()
        if not new_password or len(new_password) < 6:
            return error_response("新密码至少需要6个字符", 400)

        user = db.session.get(TUser, user_id)
        if not user:
            return error_response("用户不存在", 404)

        user.password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")
        user.must_change_password = True
        db.session.commit()

        return success_response(message="密码重置成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"重置密码失败: {str(e)}", 500)


# ═══════════════════════════════════════════════════════════════
# 作品审核
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/artworks", methods=["GET"])
@token_required
@reviewer_required
def list_artworks_for_review():
    """
    获取所有作品列表（管理员审核用）

    Query参数:
        page: 页码
        page_size: 每页数量
        review_status: 审核状态筛选
        keyword: 搜索关键词
    """
    try:
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)
        review_status = request.args.get("review_status", "").strip()
        keyword = request.args.get("keyword", "").strip()

        query = TArtwork.query

        if review_status in ("pending", "approved", "rejected"):
            query = query.filter_by(review_status=review_status)

        if keyword:
            query = query.filter(
                db.or_(
                    TArtwork.title.like(f"%{keyword}%"),
                    TArtwork.work_id.like(f"%{keyword}%"),
                )
            )

        pagination = query.order_by(TArtwork.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        artworks = []
        for a in pagination.items:
            artworks.append({
                "id": a.id,
                "work_id": a.work_id,
                "title": a.title,
                "category": a.category,
                "description": a.description,
                "images": a.images or [],
                "dna_status": a.dna_status,
                "review_status": a.review_status,
                "review_comment": a.review_comment,
                "review_grade": a.review_grade or "",
                "owner_name": a.owner.real_name if a.owner else "",
                "reviewer_name": a.reviewer.real_name if a.reviewer else "",
                "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else None,
            })

        return paginated_response(
            items=artworks,
            total=pagination.total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        return error_response(f"获取作品列表失败: {str(e)}", 500)


@admin_bp.route("/artworks/<work_id>/review", methods=["PUT"])
@token_required
@reviewer_required
def review_artwork(work_id):
    """
    审核作品（通过并评级 / 驳回）

    请求体: {
        "review_status": "approved" | "rejected",
        "review_comment": "审核意见",
        "review_grade": "master" | "premium" | "excellent" | "qualified"
    }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        review_status = data.get("review_status", "").strip()
        review_comment = data.get("review_comment", "").strip()
        review_grade = data.get("review_grade", "").strip()

        if review_status not in ("approved", "rejected"):
            return error_response("审核状态无效，应为 approved 或 rejected", 400)

        if review_status == "approved" and review_grade not in _VALID_GRADES:
            return error_response(
                f"审核通过时必须选择评级，可选: {', '.join(_VALID_GRADES)}", 400
            )

        if review_status == "rejected" and not review_comment:
            return error_response("驳回时必须填写审核意见", 400)

        artwork = TArtwork.query.filter_by(work_id=work_id).first()
        if not artwork:
            return error_response("作品不存在", 404)

        artwork.review_status = review_status
        artwork.review_comment = review_comment or None
        artwork.review_grade = review_grade or None
        artwork.reviewed_by = g.current_user["user_id"]
        artwork.reviewed_at = datetime.utcnow()
        db.session.commit()

        return success_response({
            "work_id": artwork.work_id,
            "title": artwork.title,
            "review_status": artwork.review_status,
            "review_comment": artwork.review_comment,
            "review_grade": artwork.review_grade,
        }, "审核完成")

    except Exception as e:
        db.session.rollback()
        return error_response(f"审核失败: {str(e)}", 500)


# ═══════════════════════════════════════════════════════════════
# 管理仪表盘
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/dashboard", methods=["GET"])
@token_required
@admin_required
def admin_dashboard():
    """获取管理员仪表盘统计数据"""
    try:
        total_users = TUser.query.count()
        total_works = TArtwork.query.count()
        total_certificates = TChainRecord.query.filter_by(status="success").count()
        total_verifications = TVerificationLog.query.count()
        pending_review_count = TArtwork.query.filter_by(review_status="pending").count()

        today = datetime.utcnow().date()
        today_new_users = TUser.query.filter(
            db.func.date(TUser.created_at) == today
        ).count()
        today_new_works = TArtwork.query.filter(
            db.func.date(TArtwork.created_at) == today
        ).count()

        return success_response({
            "total_users": total_users,
            "total_works": total_works,
            "total_certificates": total_certificates,
            "total_verifications": total_verifications,
            "pending_review_count": pending_review_count,
            "today_new_users": today_new_users,
            "today_new_works": today_new_works,
        })

    except Exception as e:
        return error_response(f"获取仪表盘数据失败: {str(e)}", 500)