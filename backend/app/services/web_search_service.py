"""
文化DNA —— 联网搜索服务模块

用于「双向识别 · 联网鉴定」：
上传作品图片 → 本地 AI 识别 + 联网搜索参考作品 → 上传图与联网参考图交叉比对相似度。

v2 优化（查找内容更准确）：
1. Provider 抽象层（search_providers）：Bing 为主，预留 API 型 provider 扩展点；
2. 查询构造（build_search_queries）：用户关键词 ＞ 本地 title ＞ 品类，自动清洗并补齐「非遗/品类」语境；
3. 本地参考库复用：已入库的参考图无需重复下载，按关键词直接召回参与比对；
4. 重排：先下载全部候选、逐一比对，再按相似度降序取 top-N（而非「先到先得」）；
5. 在线打分改为「语义为主」（CNN 权重更高 + 软感知哈希），更适合跨图（不同照片）比对。

联网仅用于「外部匹配查询」，无网/被拦截时优雅降级为仅本地识别。
"""
import os
import re
import pickle
import hashlib
import logging

import requests

from app.services.search_providers import SEARCH_HEADERS, search_images

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 10
_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 单张参考图上限 8MB

# ── 在线交叉比对打分权重（语义为主；与本地「实例身份识别」的 0.30/0.70 不同）──
_ONLINE_CNN_WEIGHT = 0.70
_ONLINE_DHASH_WEIGHT = 0.30
_ONLINE_MIN_SIMILARITY = 0.18   # 过滤明显无关的参考图（纯语义相似度下限）
_MAX_CANDIDATES = 18            # 参与比对的候选图上限（控制延迟）


def download_image(url, dest_path, timeout=_DEFAULT_TIMEOUT):
    """
    下载图片到本地，返回是否成功

    校验 content-type 为 image/*，并限制单张大小。
    先写入 .part 临时文件再原子改名；任何失败（非 200 / 非图片 / 超限 / 空体 / 断连）
    都会在 finally 中清理残留并关闭响应，避免留下半截/空文件被上层误当有效缓存。
    """
    tmp_path = dest_path + ".part"
    resp = None
    try:
        resp = requests.get(
            url, headers=SEARCH_HEADERS, timeout=timeout,
            stream=True, allow_redirects=True,
        )
        if resp.status_code != 200:
            return False

        ctype = (resp.headers.get("content-type") or "").lower()
        if "image" not in ctype:
            return False

        total = 0
        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > _MAX_IMAGE_BYTES:
                    return False
                f.write(chunk)

        if total == 0:
            return False
        os.replace(tmp_path, dest_path)
        return True

    except Exception as e:
        logger.warning("图片下载失败 %s: %s", url[:80], str(e))
        return False

    finally:
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _cache_filename(url):
    """根据 URL 生成缓存文件名（含正确扩展名）"""
    ext = ".jpg"
    lowered = url.lower()
    for e in (".png", ".webp", ".gif"):
        if e in lowered:
            ext = e
            break
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:16] + ext


# ══════════════════════════════════════════════════════════════════
# 查询构造
# ══════════════════════════════════════════════════════════════════

_PUNCT = re.compile(r"[，。！？、；：“”‘’（）《》【】\-,./\\:;!?()\[\]{}_|~@#$%^&*+=<>\"']+")


def _clean_query(q):
    """清洗关键词：去标点、压缩空白、截断过长文本"""
    q = (q or "").strip()
    q = _PUNCT.sub(" ", q)
    q = re.sub(r"\s+", " ", q).strip()
    if len(q) > 40:
        q = q[:40].rsplit(" ", 1)[0] if " " in q[:40] else q[:40]
    return q


def build_search_queries(user_query="", title=None, category=None):
    """
    构造一组按优先级排列的搜索关键词。

    优先级：用户自定义 ＞ 本地 top-1 标题 ＞ 品类兜底。
    返回去重后的关键词列表（不含空字符串）。
    """
    queries = []
    seen = set()

    def add(q):
        q = _clean_query(q)
        if q and q not in seen:
            seen.add(q)
            queries.append(q)

    if user_query:
        add(user_query)
        if category and category not in user_query:
            add(f"{user_query} {category}")
    if title:
        add(title)
        if category and category not in title:
            add(f"{title} {category}")
    if category:
        add(category)
        add(f"{category} 非遗")

    return queries


# ══════════════════════════════════════════════════════════════════
# 特征比对
# ══════════════════════════════════════════════════════════════════

def _soft_dhash_similarity(hash_a, hash_b):
    """
    软感知哈希相似度（0~1，按哈希总位数归一化）

    与本地「实例身份识别」的 /16 近重复尺度不同，这里用全 64 位归一化，
    在跨图（不同照片的相似作品）场景下仍保留渐变区分度。
    """
    if not hash_a or not hash_b or len(hash_a) != len(hash_b):
        return 0.0
    hamming = sum(1 for a, b in zip(hash_a, hash_b) if a != b)
    return max(0.0, 1.0 - hamming / float(len(hash_a)))


def _extract_query_features(uploaded_path):
    """
    预提取上传图特征（CNN 向量 + 感知哈希），仅在联网鉴定开始时做一次。

    Returns:
        (query_vec: np.ndarray|None, query_dhash: str|None)
    """
    try:
        import numpy as np
        from ai_model.extract import compute_dhash
        from app.services.ai_service import _get_extractor

        extractor = _get_extractor()
        vec = extractor.extract_single(uploaded_path)
        if vec is None:
            return None, None
        query_vec = np.asarray(vec, dtype=np.float32)
        return query_vec, compute_dhash(uploaded_path)
    except Exception as e:
        logger.warning("上传图特征预提取失败: %s", str(e))
        return None, None


def compare_with_ref(query_vec, query_dhash, ref_path):
    """
    上传图（特征已预提取）与单张参考图交叉比对。

    语义为主（CNN 0.70 + 软感知哈希 0.30），更适合「不同照片的相似作品」的跨图比对。

    Returns:
        {"similarity","cnn_similarity","dhash_similarity","ref_feature_bytes","ref_dhash"}
        特征提取失败返回 None。
    """
    try:
        import numpy as np
        from ai_model.extract import compute_dhash
        from app.services.ai_service import _get_extractor

        extractor = _get_extractor()
        ref_vec = extractor.extract_single(ref_path)
        if ref_vec is None:
            return None
        ref_vec = np.asarray(ref_vec, dtype=np.float32)

        cnn_sim = float(np.dot(query_vec, ref_vec))
        ref_dhash = compute_dhash(ref_path)
        dhash_sim = _soft_dhash_similarity(query_dhash, ref_dhash)
        similarity = _ONLINE_CNN_WEIGHT * cnn_sim + _ONLINE_DHASH_WEIGHT * dhash_sim

        return {
            "similarity": round(max(0.0, min(1.0, similarity)), 4),
            "cnn_similarity": round(max(0.0, min(1.0, cnn_sim)), 4),
            "dhash_similarity": round(max(0.0, dhash_sim), 4),
            "ref_feature_bytes": pickle.dumps(ref_vec.tolist()),
            "ref_dhash": ref_dhash,
        }
    except Exception as e:
        logger.warning("交叉比对失败 %s: %s", ref_path, str(e))
        return None


# ══════════════════════════════════════════════════════════════════
# 参考库持久化 / 复用
# ══════════════════════════════════════════════════════════════════

def _persist_reference(query, title, source_url, local_rel_path, image_path,
                       feat_bytes=None, dhash_str=None):
    """
    将已下载的参考图及其特征写入本地图库（t_reference_image），供长期检索

    幂等去重：同一来源 URL 只入库一次。
    feat_bytes / dhash_str 可传预计算值，避免重复 CNN 前向。
    """
    try:
        import pickle as _pickle
        import numpy as np
        from app import db
        from app.models.reference_image import TReferenceImage
        from app.services.ai_service import _get_extractor
        from ai_model.extract import compute_dhash

        # 幂等：同一来源 URL 去重
        if TReferenceImage.query.filter_by(source_url=source_url).first():
            return

        if feat_bytes is None:
            feat = _get_extractor().extract_single(image_path)
            feat_bytes = _pickle.dumps(np.asarray(feat).tolist()) if feat is not None else None
        if dhash_str is None:
            dhash_str = compute_dhash(image_path)

        rec = TReferenceImage(
            source="bing",
            search_query=query or "",
            title=(title or "")[:512],
            image_url=local_rel_path,
            source_url=source_url,
            perceptual_hash=dhash_str,
            feature_vector=feat_bytes,
        )
        db.session.add(rec)
        db.session.commit()
        logger.info("参考图已入库: %s -> %s", (title or "")[:40], local_rel_path)

    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.warning("参考图入库失败: %s", str(e))


def _query_reference_library(queries, category, upload_root, limit=6):
    """
    复用已入库的本地参考图（t_reference_image），按关键词/品类召回，避免重复联网下载。

    Returns:
        [{"title","source_url","local_path"}, ...]
    """
    try:
        from app import db
        from app.models.reference_image import TReferenceImage
        from sqlalchemy import or_

        conds = [TReferenceImage.search_query.ilike(f"%{q}%") for q in queries]
        if category:
            conds.append(TReferenceImage.search_query.ilike(f"%{category}%"))
        if not conds:
            return []

        refs = TReferenceImage.query.filter(or_(*conds)).limit(limit).all()
        out = []
        for r in refs:
            rel = (r.image_url or "").lstrip("/")
            abs_path = os.path.join(upload_root, rel) if rel else ""
            if not abs_path or not os.path.exists(abs_path):
                continue
            out.append({
                "title": r.title or "",
                "source_url": r.source_url or "",
                "local_path": abs_path,
            })
        return out
    except Exception as e:
        logger.warning("参考库复用查询失败: %s", str(e))
        return []


# ══════════════════════════════════════════════════════════════════
# 联网鉴定主流程
# ══════════════════════════════════════════════════════════════════

def online_appraise(uploaded_path, user_query="", category=None, title=None,
                    limit=4, cache_dir=None):
    """
    联网鉴定：构造查询 → 搜图（复用本地参考库 + 联网 provider）→ 交叉比对 → 重排取 top-N

    Args:
        uploaded_path: 上传图片本地路径
        user_query: 用户自定义搜索关键词（可选）
        category: 本地最佳匹配的品类（用于查询构造与参考库召回）
        title: 本地最佳匹配的标题（用于查询构造）
        limit: 返回参考作品数量上限
        cache_dir: 参考图缓存目录（uploads/online_cache，供前端本地预览）

    Returns:
        {"query","available","results": [
            {"title","source_url","image_url","similarity",
             "cnn_similarity","dhash_similarity"}, ...]}
    """
    result = {"query": "", "available": False, "results": []}

    # 1. 查询构造
    queries = build_search_queries(user_query, title, category)
    if not queries:
        return result
    result["query"] = queries[0]

    # 2. 预提取上传图特征（只做一次）
    query_vec, query_dhash = _extract_query_features(uploaded_path)
    if query_vec is None:
        return result

    # 3. 搜集候选（本地参考库复用 + 联网 provider），按 source_url 去重
    if not cache_dir:
        cache_dir = os.path.join(os.path.dirname(uploaded_path), "online_cache")
    upload_root = os.path.dirname(cache_dir) or os.path.dirname(uploaded_path)
    os.makedirs(cache_dir, exist_ok=True)

    candidates = []
    seen_urls = set()

    def push(title_, image_url_, thumb_url_=None, page_url_=None, local_path_=None, query_=None):
        # 去重键用图片 URL（实际下载主体），详情页 URL 仅用于「来源」展示
        key = image_url_ or local_path_
        if not key or key in seen_urls:
            return
        seen_urls.add(key)
        candidates.append({
            "title": title_ or "",
            "image_url": image_url_ or "",
            "thumb_url": thumb_url_ or "",
            "page_url": page_url_ or "",
            "local_path": local_path_ or "",
            "query": query_ or "",
        })

    for ref in _query_reference_library(queries, category, upload_root, limit=6):
        # 已入库参考图：source_url 即原始图片 URL，无独立详情页
        push(ref["title"], ref["source_url"], page_url_=ref["source_url"], local_path_=ref["local_path"])

    for q in queries:
        for it in search_images(q, limit=max(limit * 2, 8)):
            push(it.get("title"), it.get("image_url"),
                 thumb_url_=it.get("thumb_url"), page_url_=it.get("page_url"), query_=q)

    if not candidates:
        return result

    # 4. 逐个比对（限候选数，控制延迟）；未本地化的先下载
    compared = []
    for cand in candidates[:max(_MAX_CANDIDATES, limit * 3)]:
        ref_path = cand.get("local_path")
        newly_downloaded = False

        if not ref_path or not os.path.exists(ref_path):
            downloaded = None
            for url in (cand.get("image_url"), cand.get("thumb_url")):
                if not url:
                    continue
                fn = _cache_filename(url)
                dest = os.path.join(cache_dir, fn)
                if os.path.exists(dest):
                    downloaded = dest
                    break
                if download_image(url, dest):
                    downloaded = dest
                    break
            if not downloaded:
                continue
            ref_path = downloaded
            newly_downloaded = True

        score = compare_with_ref(query_vec, query_dhash, ref_path)
        if not score or score["similarity"] < _ONLINE_MIN_SIMILARITY:
            continue

        fn = os.path.basename(ref_path)
        compared.append({
            "title": cand.get("title") or "",
            "source_url": cand.get("page_url") or cand.get("image_url") or "",
            "image_url": f"/online_cache/{fn}",
            "similarity": score["similarity"],
            "cnn_similarity": score["cnn_similarity"],
            "dhash_similarity": score["dhash_similarity"],
        })

        if newly_downloaded:
            _persist_reference(
                cand.get("query") or queries[0],
                cand.get("title"),
                cand.get("image_url"),
                f"/online_cache/{fn}",
                ref_path,
                feat_bytes=score["ref_feature_bytes"],
                dhash_str=score["ref_dhash"],
            )

    # 5. 重排：相似度降序，取前 limit
    compared.sort(key=lambda x: x["similarity"], reverse=True)
    result["results"] = compared[:limit]
    result["available"] = len(result["results"]) > 0

    logger.info("联网鉴定完成: query=%s 参考图 %d 张", result["query"], len(result["results"]))
    return result