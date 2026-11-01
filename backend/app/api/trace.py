"""
文化DNA —— 非遗作品确权溯源系统
溯源与鉴定模块 API 路由
实现作品溯源时间线、AI+链上双重验证、所有权转让
"""
import os
import time
import uuid
from flask import Blueprint, request, g, current_app
from app import db
from app.models.artwork import TArtwork
from app.models.fingerprint import TFingerprint
from app.models.chain_record import TChainRecord
from app.models.ownership_transfer import TOwnershipTransfer
from app.models.verification_log import TVerificationLog
from app.models.user import TUser
from app.utils.response import success_response, error_response, paginated_response
from app.utils.auth_decorator import token_required, inheritor_required
from app.services.ai_service import extract_dna_features, compare_features
from app.services.blockchain_service import query_from_blockchain

trace_bp = Blueprint("trace", __name__)


# ── 作品溯源时间线 ──────────────────────────────────────────────
@trace_bp.route("/<work_id>/timeline", methods=["GET"])
@token_required
def trace_timeline(work_id):
    """
    获取作品全生命周期溯源时间线

    包含：作品创建 → DNA提取 → 区块链存证 → 所有权转让 → 鉴定记录
    所有事件按时间正序排列
    """
    try:
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        # 权限检查
        if work.user_id != g.current_user["user_id"] and g.current_user.get("role") != "admin":
            return error_response("无权查看该作品溯源信息", 403)

        timeline = []

        # 1. 作品创建事件
        timeline.append({
            "event_type": "created",
            "event_name": "作品创建",
            "timestamp": work.created_at.strftime("%Y-%m-%d %H:%M:%S") if work.created_at else None,
            "detail": {
                "title": work.title,
                "category": work.category,
                "creator": work.owner.real_name if work.owner else "",
            }
        })

        # 2. DNA提取事件
        if work.fingerprint:
            timeline.append({
                "event_type": "dna_extracted",
                "event_name": "DNA指纹提取",
                "timestamp": work.fingerprint.extracted_at.strftime("%Y-%m-%d %H:%M:%S") if work.fingerprint.extracted_at else None,
                "detail": {
                    "dna_hash": work.fingerprint.dna_hash,
                }
            })

        # 3. 区块链存证事件
        chain_records = TChainRecord.query.filter_by(work_id=work.id).order_by(
            TChainRecord.created_at.asc()
        ).all()
        for cr in chain_records:
            timeline.append({
                "event_type": "chain_record",
                "event_name": "区块链存证" if cr.status == "success" else "存证失败",
                "timestamp": cr.created_at.strftime("%Y-%m-%d %H:%M:%S") if cr.created_at else None,
                "detail": {
                    "certificate_no": cr.certificate_no,
                    "tx_id": cr.tx_id,
                    "block_height": cr.block_height,
                    "status": cr.status,
                }
            })

        # 4. 所有权转让事件
        transfers = TOwnershipTransfer.query.filter_by(work_id=work.id).order_by(
            TOwnershipTransfer.transferred_at.asc()
        ).all()
        for transfer in transfers:
            timeline.append({
                "event_type": "ownership_transfer",
                "event_name": "所有权转让",
                "timestamp": transfer.transferred_at.strftime("%Y-%m-%d %H:%M:%S") if transfer.transferred_at else None,
                "detail": {
                    "from_owner_id": transfer.from_owner,
                    "to_owner_id": transfer.to_owner,
                    "tx_id": transfer.tx_id,
                }
            })

        # 5. 鉴定记录事件
        verifications = TVerificationLog.query.filter_by(work_id=work.id).order_by(
            TVerificationLog.created_at.asc()
        ).all()
        for v in verifications:
            timeline.append({
                "event_type": "verification",
                "event_name": f"鉴定({v.verification_type})",
                "timestamp": v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else None,
                "detail": {
                    "verification_type": v.verification_type,
                    "ai_match_score": float(v.ai_match_score) if v.ai_match_score is not None else None,
                    "dna_verified": v.dna_verified,
                    "final_result": v.final_result,
                }
            })

        # 按时间排序
        timeline.sort(key=lambda x: x["timestamp"] or "")

        return success_response({
            "work_id": work.work_id,
            "title": work.title,
            "timeline": timeline,
            "total_events": len(timeline),
        })

    except Exception as e:
        return error_response(f"查询溯源时间线失败: {str(e)}", 500)


# ── AI+链上双重验证 ─────────────────────────────────────────────
@trace_bp.route("/verify", methods=["POST"])
@token_required
def verify_artwork():
    """
    对作品进行AI鉴定+DNA比对

    请求体（JSON）:
    {
        "work_id": "作品UUID",
        "image_file": "上传的鉴定图片路径"  // 或通过multipart上传
    }

    或通过multipart上传:
        work_id: 作品UUID
        verify_image: 待鉴定图片文件

    鉴定流程：
    1. 提取上传图片的DNA特征
    2. 与数据库中目标作品的特征向量做余弦相似度比对
    3. 查询区块链存证记录验证一致性
    4. 综合判定最终结果
    """
    start_time = time.time()

    try:
        # 支持JSON和multipart两种请求方式
        if request.content_type and "multipart" in request.content_type:
            work_id = request.form.get("work_id", "").strip()
            uploaded_file = request.files.get("verify_image")
        else:
            data = request.get_json(silent=True)
            if not data:
                return error_response("请求体不能为空", 400)
            work_id = data.get("work_id", "").strip()
            uploaded_file = None

        if not work_id:
            return error_response("作品编号不能为空", 400)

        # 查询目标作品
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        # 检查是否有DNA指纹
        if not work.fingerprint:
            return error_response("该作品尚未提取DNA指纹，无法进行鉴定", 400)

        verification_type = "dna_match"
        ai_match_score = None
        dna_verified = False
        final_result = "suspicious"

        if uploaded_file and uploaded_file.filename:
            # 有上传图片：进行AI视觉比对
            verification_type = "full"

            # 保存上传的鉴定图片
            upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
            verify_dir = os.path.join(upload_folder, "verify")
            os.makedirs(verify_dir, exist_ok=True)

            import uuid as uuid_mod
            ext = uploaded_file.filename.rsplit(".", 1)[1].lower() if "." in uploaded_file.filename else "jpg"
            filename = f"verify_{uuid_mod.uuid4().hex}.{ext}"
            filepath = os.path.join(verify_dir, filename)
            uploaded_file.save(filepath)

            try:
                # 提取上传图片的特征
                result = extract_dna_features([filepath], [])
                if result:
                    query_hash, query_features, _ = result

                    # 与目标作品特征向量比对
                    similarity, is_match = compare_features(
                        query_features,
                        work.fingerprint.feature_vector,
                        threshold=current_app.config.get("AI_MATCH_THRESHOLD", 0.85)
                    )
                    ai_match_score = round(similarity, 4)
                    dna_verified = is_match
            except Exception as e:
                current_app.logger.error(f"AI比对异常: {str(e)}")
                verification_type = "dna_match"
        else:
            # 无上传图片：仅做DNA指纹比对
            verification_type = "dna_match"
            dna_verified = True
            ai_match_score = 1.0

        # 查询区块链存证记录交叉验证
        chain_record = TChainRecord.query.filter_by(
            work_id=work.id,
            status="success"
        ).first()

        if chain_record:
            chain_result = query_from_blockchain(work.work_id)
            if chain_result:
                chain_dna_hash = chain_result.get("dna_hash", "")
                if chain_dna_hash == work.fingerprint.dna_hash:
                    dna_verified = dna_verified and True
                else:
                    dna_verified = False

        # 综合判定最终结果
        if ai_match_score is not None:
            if ai_match_score >= current_app.config.get("AI_MATCH_THRESHOLD", 0.85) and dna_verified:
                final_result = "authentic"
            elif ai_match_score >= 0.6 and dna_verified:
                final_result = "suspicious"
            else:
                final_result = "counterfeit"
        else:
            final_result = "authentic" if dna_verified else "suspicious"

        # 计算响应时间
        response_time_ms = int((time.time() - start_time) * 1000)

        # 记录鉴定日志
        verification_log = TVerificationLog(
            work_id=work.id,
            verification_type=verification_type,
            ai_match_score=ai_match_score,
            dna_verified=dna_verified,
            final_result=final_result,
            response_time_ms=response_time_ms,
            ip_address=request.remote_addr,
        )
        db.session.add(verification_log)
        db.session.commit()

        return success_response({
            "work_id": work.work_id,
            "title": work.title,
            "verification_type": verification_type,
            "ai_match_score": ai_match_score,
            "dna_verified": dna_verified,
            "final_result": final_result,
            "response_time_ms": response_time_ms,
            "result_label": {
                "authentic": "真品",
                "suspicious": "存疑",
                "counterfeit": "赝品",
            }.get(final_result, "未知"),
        }, "鉴定完成")

    except Exception as e:
        db.session.rollback()
        return error_response(f"鉴定失败: {str(e)}", 500)


# ── 鉴定记录查询 ────────────────────────────────────────────────
@trace_bp.route("/verification-logs", methods=["GET"])
@token_required
def list_verification_logs():
    """
    分页查询鉴定历史记录

    Query参数:
        page: 页码（默认1）
        page_size: 每页条数（默认20）
        work_id: 按作品编号筛选（可选）
        final_result: 按鉴定结果筛选（可选）
    """
    try:
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)
        filter_work_id = request.args.get("work_id", "").strip()
        final_result = request.args.get("final_result", "").strip()

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        query = TVerificationLog.query

        if filter_work_id:
            work = TArtwork.query.filter_by(work_id=filter_work_id).first()
            if work:
                query = query.filter_by(work_id=work.id)

        if final_result:
            query = query.filter_by(final_result=final_result)

        query = query.order_by(TVerificationLog.created_at.desc())

        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        items = pagination.items

        logs_list = []
        for log in items:
            logs_list.append({
                "id": log.id,
                "work_id": log.artwork.work_id if log.artwork else "",
                "work_title": log.artwork.title if log.artwork else "",
                "verification_type": log.verification_type,
                "ai_match_score": float(log.ai_match_score) if log.ai_match_score is not None else None,
                "dna_verified": log.dna_verified,
                "final_result": log.final_result,
                "response_time_ms": log.response_time_ms,
                "ip_address": log.ip_address,
                "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else None,
            })

        return paginated_response(
            items=logs_list,
            total=pagination.total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        return error_response(f"查询鉴定记录失败: {str(e)}", 500)


# ── 所有权转让 ──────────────────────────────────────────────────
@trace_bp.route("/<work_id>/transfer", methods=["POST"])
@token_required
@inheritor_required
def transfer_ownership(work_id):
    """
    作品所有权转让（上链记录）

    请求体: { "to_owner_id": 目标用户ID }
    """
    try:
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        if work.user_id != g.current_user["user_id"] and g.current_user.get("role") != "admin":
            return error_response("无权转让该作品", 403)

        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        to_owner_id = data.get("to_owner_id")
        if not to_owner_id:
            return error_response("受让方用户ID不能为空", 400)

        if to_owner_id == work.user_id:
            return error_response("不能转让给自己", 400)

        # 验证受让方是否存在
        to_user = db.session.get(TUser, to_owner_id)
        if not to_user:
            return error_response("受让方用户不存在", 404)

        # 调用区块链服务记录转让
        from app.services.blockchain_service import transfer_ownership
        chain_result = transfer_ownership(
            work_id=work.work_id,
            new_owner=str(to_owner_id),
        )

        tx_id = chain_result["tx_id"] if chain_result else ""

        # 创建转让记录
        transfer = TOwnershipTransfer(
            work_id=work.id,
            from_owner=work.user_id,
            to_owner=to_owner_id,
            tx_id=tx_id,
        )
        db.session.add(transfer)

        # 更新作品所有者
        work.user_id = to_owner_id
        db.session.commit()

        return success_response({
            "work_id": work.work_id,
            "from_owner": transfer.from_owner,
            "to_owner": transfer.to_owner,
            "tx_id": tx_id,
            "transferred_at": transfer.transferred_at.strftime("%Y-%m-%d %H:%M:%S") if transfer.transferred_at else None,
        }, "所有权转让成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"所有权转让失败: {str(e)}", 500)


# ── 转让记录查询 ────────────────────────────────────────────────
@trace_bp.route("/<work_id>/transfers", methods=["GET"])
@token_required
def list_transfers(work_id):
    """
    查询作品所有权转让记录
    """
    try:
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        if work.user_id != g.current_user["user_id"] and g.current_user.get("role") != "admin":
            return error_response("无权查看", 403)

        transfers = TOwnershipTransfer.query.filter_by(work_id=work.id).order_by(
            TOwnershipTransfer.transferred_at.asc()
        ).all()

        transfer_list = []
        for t in transfers:
            from_user = db.session.get(TUser, t.from_owner)
            to_user = db.session.get(TUser, t.to_owner)
            transfer_list.append({
                "id": t.id,
                "from_owner": t.from_owner,
                "to_owner": t.to_owner,
                "from_owner_name": from_user.real_name if from_user else "",
                "to_owner_name": to_user.real_name if to_user else "",
                "tx_id": t.tx_id,
                "transferred_at": t.transferred_at.strftime("%Y-%m-%d %H:%M:%S") if t.transferred_at else None,
            })

        return success_response({
            "work_id": work.work_id,
            "transfers": transfer_list,
            "total": len(transfer_list),
        })

    except Exception as e:
        return error_response(f"查询转让记录失败: {str(e)}", 500)


