"""
文化DNA —— 非遗作品确权溯源系统
证书与区块链存证模块 API 路由
实现DNA提取触发、上链存证、存证状态查询、证书验证
"""
import os
import uuid
from flask import Blueprint, request, g, current_app
from app import db
from app.models.artwork import TArtwork
from app.models.fingerprint import TFingerprint
from app.models.chain_record import TChainRecord
from app.utils.response import success_response, error_response, paginated_response
from app.utils.auth_decorator import token_required, inheritor_required
from app.services.ai_service import extract_dna_features
from app.services.blockchain_service import upload_to_blockchain, verify_certificate_on_chain

certificates_bp = Blueprint("certificates", __name__)


# ── 证书列表 ────────────────────────────────────────────────────
@certificates_bp.route("/", methods=["GET"])
@token_required
def list_certificates():
    """
    分页查询存证证书列表

    Query参数:
        page: 页码（默认1）
        page_size: 每页条数（默认12）
        status: 按状态筛选（可选）
    """
    try:
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 12, type=int)
        status = request.args.get("status", "").strip()

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 12

        query = TChainRecord.query

        # 非管理员只能看自己作品的存证
        if g.current_user.get("role") != "admin":
            query = query.join(TArtwork).filter(TArtwork.user_id == g.current_user["user_id"])

        if status:
            query = query.filter_by(status=status)

        query = query.order_by(TChainRecord.created_at.desc())

        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        items = pagination.items

        cert_list = []
        for record in items:
            cert_list.append({
                "id": record.id,
                "certificate_no": record.certificate_no,
                "tx_id": record.tx_id,
                "block_height": record.block_height,
                "chain_code": record.chain_code,
                "channel_name": record.channel_name,
                "status": record.status,
                "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else None,
                "work_title": record.artwork.title if record.artwork else "",
                "work_id": record.artwork.work_id if record.artwork else "",
            })

        return paginated_response(
            items=cert_list,
            total=pagination.total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        return error_response(f"查询证书列表失败: {str(e)}", 500)


# ── 证书详情 ────────────────────────────────────────────────────
@certificates_bp.route("/<certificate_no>", methods=["GET"])
@token_required
def get_certificate(certificate_no):
    """
    根据证书编号获取详情（含区块链存证信息）
    """
    try:
        record = TChainRecord.query.filter_by(certificate_no=certificate_no).first()
        if not record:
            return error_response("证书不存在", 404)

        # 权限检查
        if g.current_user.get("role") != "admin":
            if not record.artwork or record.artwork.user_id != g.current_user["user_id"]:
                return error_response("无权查看该证书", 403)

        cert_detail = {
            "certificate_no": record.certificate_no,
            "tx_id": record.tx_id,
            "block_height": record.block_height,
            "chain_code": record.chain_code,
            "channel_name": record.channel_name,
            "status": record.status,
            "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else None,
            "work": {
                "work_id": record.artwork.work_id,
                "title": record.artwork.title,
                "category": record.artwork.category,
                "dna_hash": record.artwork.fingerprint.dna_hash if record.artwork and record.artwork.fingerprint else None,
            } if record.artwork else None,
        }

        return success_response(cert_detail)

    except Exception as e:
        return error_response(f"查询证书详情失败: {str(e)}", 500)


# ── 上链存证 ────────────────────────────────────────────────────
@certificates_bp.route("/<work_id>", methods=["POST"])
@token_required
@inheritor_required
def create_certificate(work_id):
    """
    触发DNA提取+上链存证

    流程：
    1. 检查作品DNA指纹是否已提取
    2. 若未提取，先触发AI特征提取
    3. 调用区块链服务上传存证
    4. 生成存证记录写入数据库

    Path参数: work_id - 作品UUID
    """
    try:
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        if work.user_id != g.current_user["user_id"] and g.current_user.get("role") != "admin":
            return error_response("无权操作该作品", 403)

        # 检查是否已有成功存证
        existing = TChainRecord.query.filter_by(
            work_id=work.id,
            status="success"
        ).first()
        if existing:
            return error_response("该作品已成功上链存证，请勿重复操作", 409)

        # 确保DNA指纹已提取
        if not work.fingerprint or work.dna_status != "completed":
            if not work.images or not work.microscope_images:
                return error_response("请先上传作品图片和微观图像", 400)

            work.dna_status = "processing"
            db.session.commit()

            try:
                upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
                image_paths = [os.path.join(upload_folder, img.lstrip("/")) for img in work.images]
                microscope_paths = [os.path.join(upload_folder, img.lstrip("/")) for img in work.microscope_images]

                result = extract_dna_features(image_paths, microscope_paths)
                if result is None:
                    work.dna_status = "failed"
                    db.session.commit()
                    return error_response("DNA特征提取失败", 500)

                dna_hash, feature_tensor, perceptual_hash = result

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

            except Exception as e:
                work.dna_status = "failed"
                db.session.commit()
                return error_response(f"DNA提取异常: {str(e)}", 500)

        # 生成证书编号
        certificate_no = f"CERT-{uuid.uuid4().hex[:16].upper()}"

        # 调用区块链服务上链
        metadata = {
            "work_id": work.work_id,
            "title": work.title,
            "category": work.category,
            "dna_hash": work.fingerprint.dna_hash,
            "owner": work.owner.real_name if work.owner else "",
        }

        chain_result = upload_to_blockchain(
            work_id=work.work_id,
            dna_hash=work.fingerprint.dna_hash,
            certificate_no=certificate_no,
            metadata=metadata,
        )

        if chain_result is None:
            # 上链失败，但DNA已提取，记录失败状态
            chain_record = TChainRecord(
                work_id=work.id,
                certificate_no=certificate_no,
                tx_id="",
                block_height=0,
                chain_code=current_app.config.get("FABRIC_CHAINCODE", "artworkcc"),
                channel_name=current_app.config.get("FABRIC_CHANNEL", "culturaldnachannel"),
                status="failed",
            )
            db.session.add(chain_record)
            db.session.commit()
            return error_response("区块链上链失败，请重试", 500)

        # 创建存证记录
        chain_record = TChainRecord(
            work_id=work.id,
            certificate_no=certificate_no,
            tx_id=chain_result["tx_id"],
            block_height=chain_result["block_height"],
            chain_code=chain_result["chain_code"],
            channel_name=chain_result["channel_name"],
            status="success",
        )
        db.session.add(chain_record)
        db.session.commit()

        return success_response({
            "certificate_no": certificate_no,
            "tx_id": chain_result["tx_id"],
            "block_height": chain_result["block_height"],
            "dna_hash": work.fingerprint.dna_hash,
            "status": "success",
        }, "上链存证成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"存证失败: {str(e)}", 500)


# ── 查询存证状态 ────────────────────────────────────────────────
@certificates_bp.route("/<work_id>/status", methods=["GET"])
@token_required
def get_certificate_status(work_id):
    """
    查询作品存证状态

    返回DNA状态和最新存证记录
    """
    try:
        work = TArtwork.query.filter_by(work_id=work_id).first()
        if not work:
            return error_response("作品不存在", 404)

        if work.user_id != g.current_user["user_id"] and g.current_user.get("role") != "admin":
            return error_response("无权查看", 403)

        latest_record = TChainRecord.query.filter_by(work_id=work.id).order_by(
            TChainRecord.created_at.desc()
        ).first()

        return success_response({
            "work_id": work.work_id,
            "dna_status": work.dna_status,
            "dna_hash": work.fingerprint.dna_hash if work.fingerprint else None,
            "certificate": {
                "certificate_no": latest_record.certificate_no,
                "tx_id": latest_record.tx_id,
                "block_height": latest_record.block_height,
                "status": latest_record.status,
                "created_at": latest_record.created_at.strftime("%Y-%m-%d %H:%M:%S") if latest_record and latest_record.created_at else None,
            } if latest_record else None,
        })

    except Exception as e:
        return error_response(f"查询存证状态失败: {str(e)}", 500)


# ── 验证证书 ────────────────────────────────────────────────────
@certificates_bp.route("/<certificate_no>/verify", methods=["POST"])
def verify_certificate_public(certificate_no):
    """
    验证证书真伪（公开接口，无需登录）

    在区块链上验证证书是否存在且未被篡改
    """
    try:
        # 先从数据库查询
        record = TChainRecord.query.filter_by(certificate_no=certificate_no).first()
        if not record:
            return error_response("证书不存在", 404)

        # 调用区块链服务验证（链上记录以作品 UUID 为键，而非数据库自增主键）
        chain_result = verify_certificate_on_chain(
            certificate_no,
            work_id=record.artwork.work_id if record.artwork else None,
        )

        is_valid = False
        if chain_result and chain_result.get("is_valid"):
            is_valid = True

        # 关联作品信息（供前端「关联作品」卡片展示）
        work_info = None
        if record.artwork:
            work_info = {
                "work_id": record.artwork.work_id,
                "title": record.artwork.title,
                "category": record.artwork.category,
                "dna_hash": record.artwork.fingerprint.dna_hash if record.artwork.fingerprint else None,
                "owner_name": record.artwork.owner.real_name if record.artwork.owner else "",
                "created_at": record.artwork.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.artwork.created_at else None,
            }

        return success_response({
            "certificate_no": certificate_no,
            "is_valid": is_valid,
            "db_record": {
                "certificate_no": record.certificate_no,
                "tx_id": record.tx_id,
                "block_height": record.block_height,
                "chain_code": record.chain_code,
                "channel_name": record.channel_name,
                "status": record.status,
                "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else None,
            },
            "chain_record": chain_result.get("chain_record") if chain_result else None,
            "work_info": work_info,
        })

    except Exception as e:
        return error_response(f"验证证书失败: {str(e)}", 500)