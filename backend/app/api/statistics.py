"""
文化DNA —— 非遗作品确权溯源系统
数据统计模块 API 路由
实现仪表盘概览、趋势分析、品类分布、活跃传承人统计
"""
from datetime import datetime, timedelta
from flask import Blueprint, request
from sqlalchemy import func
from app import db
from app.models.artwork import TArtwork
from app.models.chain_record import TChainRecord
from app.models.verification_log import TVerificationLog
from app.models.user import TUser
from app.models.fingerprint import TFingerprint
from app.models.reference_image import TReferenceImage
from app.models.publish_record import TPublishRecord
from app.utils.response import success_response, error_response
from app.utils.auth_decorator import token_required, admin_required

statistics_bp = Blueprint("statistics", __name__)


# ── 仪表盘概览 ──────────────────────────────────────────────────
@statistics_bp.route("/overview", methods=["GET"])
@token_required
@admin_required
def dashboard():
    """
    管理后台仪表盘数据

    返回：
    - 存证总数
    - 验证总数
    - 今日新增作品
    - 验证通过率
    - 作品总数
    - 用户总数
    """
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # 作品总数
        total_works = db.session.query(func.count(TArtwork.id)).scalar() or 0

        # 存证总数（成功）
        total_certificates = db.session.query(func.count(TChainRecord.id)).filter(
            TChainRecord.status == "success"
        ).scalar() or 0

        # 验证总数
        total_verifications = db.session.query(func.count(TVerificationLog.id)).scalar() or 0

        # 今日新增作品
        today_works = db.session.query(func.count(TArtwork.id)).filter(
            TArtwork.created_at >= today
        ).scalar() or 0

        # 今日新增存证
        today_certificates = db.session.query(func.count(TChainRecord.id)).filter(
            TChainRecord.created_at >= today,
            TChainRecord.status == "success"
        ).scalar() or 0

        # 今日鉴定次数
        today_verifications = db.session.query(func.count(TVerificationLog.id)).filter(
            TVerificationLog.created_at >= today
        ).scalar() or 0

        # 验证通过率
        authentic_count = db.session.query(func.count(TVerificationLog.id)).filter(
            TVerificationLog.final_result == "authentic"
        ).scalar() or 0

        pass_rate = round(authentic_count / total_verifications * 100, 2) if total_verifications > 0 else 0.0

        # 用户总数
        total_users = db.session.query(func.count(TUser.id)).scalar() or 0

        # DNA提取完成率
        dna_completed = db.session.query(func.count(TArtwork.id)).filter(
            TArtwork.dna_status == "completed"
        ).scalar() or 0
        dna_rate = round(dna_completed / total_works * 100, 2) if total_works > 0 else 0.0

        # 本地数据库规模（指纹库 / 联网参考图库 / 网络发布台账）
        total_fingerprints = db.session.query(func.count(TFingerprint.id)).scalar() or 0
        total_references = db.session.query(func.count(TReferenceImage.id)).scalar() or 0
        total_published = db.session.query(func.count(TPublishRecord.id)).filter(
            TPublishRecord.status == "success"
        ).scalar() or 0

        return success_response({
            "total_works": total_works,
            "total_certificates": total_certificates,
            "total_verifications": total_verifications,
            "total_users": total_users,
            "total_fingerprints": total_fingerprints,
            "total_references": total_references,
            "total_published": total_published,
            "today_works": today_works,
            "today_certificates": today_certificates,
            "today_verifications": today_verifications,
            "verification_pass_rate": pass_rate,
            "dna_completion_rate": dna_rate,
        })

    except Exception as e:
        return error_response(f"获取仪表盘数据失败: {str(e)}", 500)


# ── 近N天存证/验证趋势 ──────────────────────────────────────────
@statistics_bp.route("/trend", methods=["GET"])
@token_required
@admin_required
def trend():
    """
    近N天存证/验证趋势

    Query参数:
        days: 天数（默认30天）
    """
    try:
        days = request.args.get("days", 30, type=int)
        if days < 1 or days > 365:
            days = 30

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = today - timedelta(days=days - 1)

        trend_data = []

        for i in range(days):
            date_start = start_date + timedelta(days=i)
            date_end = date_start + timedelta(days=1)

            # 当天存证数
            cert_count = db.session.query(func.count(TChainRecord.id)).filter(
                TChainRecord.created_at >= date_start,
                TChainRecord.created_at < date_end,
                TChainRecord.status == "success"
            ).scalar() or 0

            # 当天验证数
            verify_count = db.session.query(func.count(TVerificationLog.id)).filter(
                TVerificationLog.created_at >= date_start,
                TVerificationLog.created_at < date_end
            ).scalar() or 0

            trend_data.append({
                "date": date_start.strftime("%Y-%m-%d"),
                "certificates": cert_count,
                "verifications": verify_count,
            })

        return success_response({
            "days": days,
            "trend": trend_data,
        })

    except Exception as e:
        return error_response(f"获取趋势数据失败: {str(e)}", 500)


# ── 各品类作品数量占比 ──────────────────────────────────────────
@statistics_bp.route("/category", methods=["GET"])
@token_required
@admin_required
def category():
    """
    各品类作品数量及占比
    """
    try:
        results = db.session.query(
            TArtwork.category,
            func.count(TArtwork.id).label("count")
        ).group_by(TArtwork.category).order_by(func.count(TArtwork.id).desc()).all()

        total = sum(row.count for row in results) if results else 0

        category_data = []
        for row in results:
            category_data.append({
                "category": row.category,
                "count": row.count,
                "percentage": round(row.count / total * 100, 2) if total > 0 else 0.0,
            })

        return success_response({
            "total": total,
            "categories": category_data,
        })

    except Exception as e:
        return error_response(f"获取品类统计失败: {str(e)}", 500)


# ── 活跃传承人Top5 ──────────────────────────────────────────────
@statistics_bp.route("/top-creators", methods=["GET"])
@token_required
@admin_required
def top_creators():
    """
    活跃传承人Top5（按作品数量排序）
    """
    try:
        results = db.session.query(
            TUser.id,
            TUser.real_name,
            TUser.username,
            func.count(TArtwork.id).label("work_count"),
            func.count(TChainRecord.id).label("cert_count"),
        ).join(
            TArtwork, TArtwork.user_id == TUser.id
        ).outerjoin(
            TChainRecord,
            (TChainRecord.work_id == TArtwork.id) & (TChainRecord.status == "success")
        ).filter(
            TUser.role == "inheritor"
        ).group_by(
            TUser.id
        ).order_by(
            func.count(TArtwork.id).desc()
        ).limit(5).all()

        top_creators = []
        for row in results:
            # 额外查询该传承人的鉴定通过率
            verify_total = db.session.query(func.count(TVerificationLog.id)).join(
                TArtwork, TVerificationLog.work_id == TArtwork.id
            ).filter(
                TArtwork.user_id == row.id
            ).scalar() or 0

            verify_authentic = db.session.query(func.count(TVerificationLog.id)).join(
                TArtwork, TVerificationLog.work_id == TArtwork.id
            ).filter(
                TArtwork.user_id == row.id,
                TVerificationLog.final_result == "authentic"
            ).scalar() or 0

            pass_rate = round(verify_authentic / verify_total * 100, 2) if verify_total > 0 else 0.0

            top_creators.append({
                "user_id": row.id,
                "real_name": row.real_name,
                "username": row.username,
                "work_count": row.work_count,
                "cert_count": row.cert_count,
                "verification_pass_rate": pass_rate,
            })

        return success_response({
            "top_creators": top_creators,
        })

    except Exception as e:
        return error_response(f"获取活跃传承人统计失败: {str(e)}", 500)