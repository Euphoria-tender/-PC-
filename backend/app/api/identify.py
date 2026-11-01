"""
文化DNA —— 特征点识别模块 API 路由
1:N identification —— 拍摄图片自动识别作品
"""
import os
import uuid
import time
from flask import Blueprint, request, current_app
from app import db
from app.models.artwork import TArtwork
from app.models.fingerprint import TFingerprint
from app.models.verification_log import TVerificationLog
from app.utils.response import success_response, error_response
from app.utils.auth_decorator import token_required
from app.services.ai_service import identify_artwork

identify_bp = Blueprint("identify", __name__)


@identify_bp.route("/identify", methods=["POST"])
@token_required
def identify():
    """
    1:N 特征点识别

    上传一张作品特征点图片，AI 自动识别是数据库中的哪件作品。

    请求格式: multipart/form-data
        identify_image: 待识别的图片文件
        top_k: 返回最佳匹配数量（可选，默认5，最大20）

    返回:
        {
            "code": 0,
            "data": {
                "matches": [...],
                "total_in_database": 100,
                "response_time_ms": 250
            }
        }
    """
    start_time = time.time()

    try:
        # 验证文件上传
        if "identify_image" not in request.files:
            return error_response("请上传待识别图片", 400)

        uploaded_file = request.files["identify_image"]
        if not uploaded_file.filename:
            return error_response("请选择图片文件", 400)

        # 校验文件扩展名
        filename = uploaded_file.filename
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", {"png", "jpg", "jpeg", "webp"})
        if ext not in allowed:
            return error_response(f"不支持的图片格式: {ext}，支持 {', '.join(allowed)}", 400)

        # 保存上传的图片
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
        identify_dir = os.path.join(upload_folder, "identify")
        os.makedirs(identify_dir, exist_ok=True)

        saved_filename = f"identify_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(identify_dir, saved_filename)
        uploaded_file.save(filepath)

        # 获取参数
        top_k = request.form.get("top_k", 5, type=int)
        if top_k < 1 or top_k > 20:
            top_k = 5

        threshold = current_app.config.get("AI_MATCH_THRESHOLD", 0.85)

        # 执行识别
        matches = identify_artwork(filepath, threshold=threshold, top_k=top_k)

        response_time_ms = int((time.time() - start_time) * 1000)

        # 记录识别日志（最佳匹配）
        if matches:
            best_match = matches[0]
            work = TArtwork.query.filter_by(work_id=best_match["work_id"]).first()
            if work:
                log = TVerificationLog(
                    work_id=work.id,
                    verification_type="identify",
                    ai_match_score=best_match["similarity"],
                    dna_verified=best_match["is_match"],
                    final_result="authentic" if best_match["is_match"] else "suspicious",
                    response_time_ms=response_time_ms,
                    ip_address=request.remote_addr,
                )
                db.session.add(log)
                db.session.commit()

        # 统计数据库中可用指纹总数
        total_count = TFingerprint.query.count()

        return success_response({
            "matches": matches,
            "total_in_database": total_count,
            "response_time_ms": response_time_ms,
        }, "识别完成")

    except Exception as e:
        db.session.rollback()
        return error_response(f"识别失败: {str(e)}", 500)


@identify_bp.route("/identify/online", methods=["POST"])
@token_required
def identify_online():
    """
    双向识别 · 联网鉴定

    上传作品图片后：
    1. 本地 AI 识别（与 /identify 相同，识别「具体是哪一件作品」）
    2. 联网搜索参考作品（Bing 图片搜索，免密钥）
    3. 上传图与联网参考图逐一交叉比对，给出相似度 → 鉴定

    请求格式: multipart/form-data
        identify_image: 待识别图片
        top_k: 本地识别返回数量（可选，默认5）
        query: 联网搜索关键词（可选，缺省用本地最佳匹配的题目）

    返回:
        { "code":0, "data": {
            "local": { "matches":[...], "total_in_database":N, "response_time_ms":X },
            "online": { "query":"...", "available":bool,
                        "results":[{title,source_url,image_url,similarity,cnn_similarity,dhash_similarity}] }
        } }
    """
    start_time = time.time()

    try:
        # 校验并保存上传图片
        if "identify_image" not in request.files:
            return error_response("请上传待识别图片", 400)
        uploaded_file = request.files["identify_image"]
        if not uploaded_file.filename:
            return error_response("请选择图片文件", 400)

        filename = uploaded_file.filename
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", {"png", "jpg", "jpeg", "webp"})
        if ext not in allowed:
            return error_response(f"不支持的图片格式: {ext}，支持 {', '.join(sorted(allowed))}", 400)

        upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
        identify_dir = os.path.join(upload_folder, "identify")
        os.makedirs(identify_dir, exist_ok=True)
        saved_filename = f"identify_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(identify_dir, saved_filename)
        uploaded_file.save(filepath)

        top_k = request.form.get("top_k", 5, type=int)
        if top_k < 1 or top_k > 20:
            top_k = 5
        user_query = request.form.get("query", "").strip()
        threshold = current_app.config.get("AI_MATCH_THRESHOLD", 0.85)

        # 1. 本地识别
        local_matches = identify_artwork(filepath, threshold=threshold, top_k=top_k)
        local_resp = {
            "matches": local_matches,
            "total_in_database": TFingerprint.query.count(),
            "response_time_ms": int((time.time() - start_time) * 1000),
        }

        # 2. 联网搜索 + 交叉比对（失败则优雅降级为仅本地）
        online_resp = {"query": user_query, "available": False, "results": []}
        category = local_matches[0]["category"] if local_matches else None
        title = local_matches[0]["title"] if local_matches else None

        try:
            from app.services.web_search_service import online_appraise
            cache_dir = os.path.join(upload_folder, "online_cache")
            online_resp = online_appraise(
                filepath,
                user_query=user_query,
                category=category,
                title=title,
                limit=4,
                cache_dir=cache_dir,
            )
        except Exception as e:
            current_app.logger.warning("联网鉴定异常: %s", str(e))
            online_resp["available"] = False

        # 记录识别日志（本地最佳匹配）
        if local_matches:
            best = local_matches[0]
            work = TArtwork.query.filter_by(work_id=best["work_id"]).first()
            if work:
                log = TVerificationLog(
                    work_id=work.id,
                    verification_type="identify_online",
                    ai_match_score=best["similarity"],
                    dna_verified=best["is_match"],
                    final_result="authentic" if best["is_match"] else "suspicious",
                    response_time_ms=int((time.time() - start_time) * 1000),
                    ip_address=request.remote_addr,
                )
                db.session.add(log)
                db.session.commit()

        return success_response({
            "local": local_resp,
            "online": online_resp,
            "response_time_ms": int((time.time() - start_time) * 1000),
        }, "双向识别完成")

    except Exception as e:
        db.session.rollback()
        return error_response(f"联网鉴定失败: {str(e)}", 500)