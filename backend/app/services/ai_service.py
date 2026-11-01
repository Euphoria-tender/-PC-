"""
文化DNA —— 非遗作品确权溯源系统
AI特征提取服务模块
对接 ai_model 模块，为API层提供作品DNA特征提取与比对能力
"""
import os
import sys
import pickle
import hashlib
import logging
from typing import Optional, Tuple, List

# 将 ai_model 目录加入 Python 路径（确保跨模块导入）
# 桌面版：ai_model 在 backend/ 目录下，即 app/services/ 向上两级
_AI_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ai_model")
)
if _AI_MODEL_DIR not in sys.path:
    sys.path.insert(0, _AI_MODEL_DIR)

logger = logging.getLogger(__name__)

# ── 全局特征提取器实例（懒加载，服务启动时预热） ────────────────
_extractor = None


def _get_extractor() -> object:
    """
    获取全局特征提取器单例（懒加载）

    首次调用时加载模型，后续调用直接复用。
    避免每次请求都重新加载模型导致的冷启动延迟。

    Returns:
        FeatureExtractor 实例
    """
    global _extractor
    if _extractor is None:
        try:
            from ai_model.extract import FeatureExtractor

            # 模型权重路径
            checkpoint_path = os.environ.get(
                "AI_MODEL_PATH",
                os.path.join(_AI_MODEL_DIR, "checkpoints", "best.pth")
            )

            # 如果checkpoint不存在，使用ImageNet预训练权重
            if not os.path.exists(checkpoint_path):
                logger.warning(
                    "模型权重文件不存在: %s，将使用 ImageNet 预训练权重（初始状态）",
                    checkpoint_path
                )
                checkpoint_path = None

            _extractor = FeatureExtractor(checkpoint_path=checkpoint_path)
            logger.info("AI特征提取器初始化完成")

        except Exception as e:
            logger.error("AI特征提取器初始化失败: %s", str(e))
            raise RuntimeError(f"AI模型加载失败: {str(e)}")

    return _extractor


def warmup_model() -> bool:
    """
    服务启动时预热模型

    在 Flask 应用启动后调用，提前加载模型到内存/显存，
    避免首次请求时的冷启动延迟。

    使用方式（在 app/__init__.py 中）：
        from app.services.ai_service import warmup_model
        with app.app_context():
            warmup_model()

    Returns:
        预热是否成功
    """
    try:
        extractor = _get_extractor()
        logger.info("AI模型预热完成，设备: %s", extractor.device)
        return True
    except Exception as e:
        logger.error("AI模型预热失败: %s", str(e))
        return False


# ══════════════════════════════════════════════════════════════════
# 对外 API（供 app/api/ 层调用）
# ══════════════════════════════════════════════════════════════════

def extract_dna_features(
    image_paths: List[str],
    microscope_paths: List[str],
) -> Optional[Tuple[str, bytes]]:
    """
    从作品图片和微观图像中提取AI特征向量（完整实现）

    流程：
    1. 获取全局特征提取器
    2. 调用 extractor.extract() 融合普通图片和微观图像特征
    3. 返回DNA哈希和序列化后的特征向量

    Args:
        image_paths: 作品普通图片路径列表
        microscope_paths: 微观扫描图像路径列表

    Returns:
        (dna_hash, feature_vector_bytes, perceptual_hash) 元组
        dna_hash: SHA-256哈希字符串（用于存证和链上记录）
        feature_vector_bytes: pickle序列化后的特征向量（存入 t_fingerprint）
        perceptual_hash: 64位 dHash 字符串（用于「识别具体是哪一件作品」）
        提取失败返回 None
    """
    try:
        extractor = _get_extractor()

        result = extractor.extract(image_paths, microscope_paths)
        if result is None:
            logger.error("特征提取失败: 无有效图片")
            return None

        dna_hash, feature_vector = result

        # 序列化特征向量为二进制（存入数据库 BLOB 字段）
        feature_bytes = pickle.dumps(feature_vector.tolist())

        # 计算感知哈希（从首张作品图），用于实例级身份匹配
        from ai_model.extract import compute_dhash
        dhash_str = compute_dhash(image_paths[0]) if image_paths else None

        logger.info(
            "DNA特征提取成功: hash=%s..., dim=%d, dhash=%s",
            dna_hash[:16],
            len(feature_vector),
            (dhash_str or "")[:16],
        )
        return dna_hash, feature_bytes, dhash_str

    except Exception as e:
        logger.error("特征提取异常: %s", str(e))
        return None


def compare_features(
    query_features: bytes,
    target_features: bytes,
    threshold: float = 0.85,
) -> Tuple[float, bool]:
    """
    比对两个特征向量，计算余弦相似度（完整实现）

    用于鉴定流程：将上传图片的特征与数据库中的作品特征进行比对

    Args:
        query_features: 查询图像的特征向量（二进制，pickle序列化）
        target_features: 目标作品的特征向量（二进制，pickle序列化）
        threshold: 匹配阈值，默认0.85

    Returns:
        (similarity_score, is_match)
        similarity_score: 余弦相似度分数 (0.0 ~ 1.0)
        is_match: 是否达到匹配阈值
    """
    try:
        from ai_model.extract import compare_feature_vectors

        similarity, is_match = compare_feature_vectors(
            query_features,
            target_features,
            threshold,
        )
        return similarity, is_match

    except Exception as e:
        logger.error("特征比对异常: %s", str(e))
        return 0.0, False


def generate_dna_hash_from_vector(feature_vector: list) -> str:
    """
    从特征向量生成DNA哈希值（SHA-256）

    用途：从数据库中已存储的特征向量重新生成哈希，用于链上验证

    Args:
        feature_vector: 特征向量列表

    Returns:
        SHA-256哈希字符串
    """
    feature_str = ",".join(f"{v:.6f}" for v in feature_vector)
    return hashlib.sha256(feature_str.encode("utf-8")).hexdigest()


def identify_artwork(
    image_path: str,
    threshold: float = 0.85,
    top_k: int = 5,
) -> List[dict]:
    """
    1:N 特征点识别 —— 拍摄图片，识别是数据库中的哪件作品

    与数据库中所有已提取指纹的作品逐一比对，返回相似度最高的 top_k 个结果。

    Args:
        image_path: 待识别图片的本地路径
        threshold: 匹配阈值（余弦相似度），默认0.85
        top_k: 返回最佳匹配数量，默认5

    Returns:
        匹配结果列表，按相似度降序排列：
        [
            {
                "work_id": "...",
                "title": "...",
                "category": "...",
                "description": "...",
                "similarity": 0.95,
                "is_match": True,
                "dna_hash": "...",
                "owner_name": "...",
                "images": [...] / None,
            },
            ...
        ]
        未找到匹配时返回空列表。
    """
    try:
        import numpy as np
        from app import db
        from app.models.fingerprint import TFingerprint
        from app.models.artwork import TArtwork

        # 1. 提取待识别图片的特征向量 + 感知哈希
        extractor = _get_extractor()
        feat = extractor.extract_single(image_path)
        if feat is None:
            logger.warning("识别失败: 无法从图片中提取特征")
            return []

        from ai_model.extract import compute_dhash, dhash_similarity

        query_vec = np.array(feat)
        query_dhash = compute_dhash(image_path)

        # 2. 查询所有已提取指纹的作品（跳过已驳回的）
        fingerprints = (
            db.session.query(TFingerprint, TArtwork)
            .join(TArtwork, TFingerprint.work_id == TArtwork.id)
            .filter(TArtwork.review_status != "rejected")
            .all()
        )

        if not fingerprints:
            logger.info("识别: 数据库中无可用指纹记录")
            return []

        # 3. 逐一比对：CNN 余弦相似度 + 感知哈希联合打分
        #    感知哈希负责「识别具体是哪一件作品」（实例身份），
        #    CNN 特征负责语义排序（打散视觉相近但确属不同的作品）。
        results = []
        for fp, artwork in fingerprints:
            try:
                target_vec = np.array(pickle.loads(fp.feature_vector))
                # CNN 余弦相似度 = 点积（向量已 L2 归一化）
                cnn_sim = float(np.dot(query_vec, target_vec))
                # 感知哈希相似度（1 - 汉明距离/64）
                dhash_sim = dhash_similarity(query_dhash, fp.perceptual_hash)
                # 联合分数（感知哈希为主）
                similarity = 0.30 * cnn_sim + 0.70 * dhash_sim
                is_match = similarity >= threshold

                results.append({
                    "work_id": artwork.work_id,
                    "title": artwork.title,
                    "category": artwork.category,
                    "description": artwork.description or "",
                    "similarity": round(similarity, 4),
                    "is_match": is_match,
                    "dna_hash": fp.dna_hash,
                    "owner_name": artwork.owner.real_name if artwork.owner else "",
                    "images": artwork.images or [],
                    "source_url": artwork.source_url or "",
                })
            except Exception as e:
                logger.warning("比对指纹 %s 时出错: %s", fp.dna_hash[:16], str(e))
                continue

        # 4. 按相似度降序排列，返回 top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        logger.info(
            "识别完成: %d 个指纹比对, 最佳匹配=%s 相似度=%.4f",
            len(results),
            results[0]["title"] if results else "无",
            results[0]["similarity"] if results else 0,
        )
        return results[:top_k]

    except Exception as e:
        logger.error("识别异常: %s", str(e))
        return []