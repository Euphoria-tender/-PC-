"""
文化DNA —— AI 特征提取模块 v2
基于 ResNet50 (ImageNet 预训练) 的深度特征提取器
输出 L2 归一化嵌入向量（默认 use_projector=False → 2048 维；
启用投影头时为 128 维），支持 1:1 验证和 1:N 识别

架构:
    ResNet50 (torchvision, weights=None, 离线) → backbone 2048-dim
    （可选投影头）Linear(2048→512) → BatchNorm → ReLU
    → Linear(512→128) → L2-Normalize

若 PyTorch 不可用，自动降级为传统 CV 方法（感知哈希 + 颜色直方图）
"""
import os
import logging
import pickle
import hashlib
import numpy as np

logger = logging.getLogger(__name__)

# ── 尝试加载 PyTorch ────────────────────────────────────────────
_TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    import torchvision.transforms as transforms
    from torchvision import models
    _TORCH_AVAILABLE = True
    logger.info("PyTorch 已加载，将使用 ResNet50 深度特征提取器")
except ImportError:
    logger.warning("PyTorch 不可用，降级为传统 CV 特征提取器")


# ══════════════════════════════════════════════════════════════════
# ResNet50 特征提取器
# ══════════════════════════════════════════════════════════════════
if _TORCH_AVAILABLE:
    class ResNet50Extractor(nn.Module):
        """ResNet50 → 2048-dim（use_projector=True 时经投影头 → 128-dim）"""

        def __init__(self, checkpoint_path=None, freeze_backbone=True, use_projector=True):
            super().__init__()
            self.use_projector = use_projector
            # 构建 ResNet50 架构（不联网下载预训练权重：离线下统一从本地 checkpoint 恢复）
            backbone = models.resnet50(weights=None)
            # 去掉最后的 FC 层
            self.backbone = nn.Sequential(*list(backbone.children())[:-1])
            self.backbone_dim = 2048

            if freeze_backbone:
                for param in self.backbone.parameters():
                    param.requires_grad = False

            if use_projector:
                # 投影头: 2048 → 512 → 128（固定随机种子确保一致性）
                torch.manual_seed(42)
                self.projector = nn.Sequential(
                    nn.Linear(2048, 512),
                    nn.BatchNorm1d(512),
                    nn.ReLU(inplace=True),
                    nn.Linear(512, 128),
                )
                self.output_dim = 128
            else:
                self.projector = None
                self.output_dim = 2048

            # 从本地 checkpoint 恢复权重（backbone 含 ImageNet 预训练权重），
            # 保证离线运行，不依赖 torchvision 联网下载。
            loaded = False
            if checkpoint_path and os.path.exists(checkpoint_path):
                try:
                    state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
                    if isinstance(state, dict) and "model_state_dict" in state:
                        state = state["model_state_dict"]
                    self.load_state_dict(state, strict=False)
                    loaded = True
                    logger.info("已加载模型权重: %s", checkpoint_path)
                except Exception as e:
                    logger.warning("加载模型权重失败: %s", str(e))
            if not loaded:
                logger.warning("未找到本地模型权重，识别效果可能受限")

            self.device = "cpu"
            self.eval()

        def forward(self, x):
            feat = self.backbone(x)
            feat = feat.view(feat.size(0), -1)  # (B, 2048)
            if self.projector is not None:
                embed = self.projector(feat)     # (B, 128)
            else:
                embed = feat                     # (B, 2048) — 直接用骨干特征
            return nn.functional.normalize(embed, p=2, dim=1)


class FeatureExtractor:
    """
    统一特征提取器接口

    优先使用 ResNet50 深度模型，不可用时降级为传统 CV 方法
    """

    def __init__(self, checkpoint_path=None, use_projector=False):
        self.use_torch = _TORCH_AVAILABLE
        self.device = "cpu"

        if self.use_torch:
            self.model = ResNet50Extractor(
                checkpoint_path=checkpoint_path,
                use_projector=use_projector
            )
            self.model.eval()
            # 图像预处理
            self.transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                ),
            ])
            logger.info("FeatureExtractor v2 初始化完成 (ResNet50, device=%s)", self.device)
        else:
            self.model = None
            self.transform = None
            logger.info("FeatureExtractor 初始化完成 (传统CV模式)")

    def extract_single(self, image_path):
        """
        从单张图片提取特征向量（L2 归一化）

        Args:
            image_path: 图片文件路径

        Returns:
            numpy array shape (2048,)（默认 use_projector=False）
            或 (128,)（use_projector=True），L2 归一化；失败返回 None
        """
        if self.use_torch:
            return self._extract_torch(image_path)
        else:
            return self._extract_cv(image_path)

    def _extract_torch(self, image_path):
        """使用 ResNet50 提取特征"""
        try:
            from PIL import Image
            img = Image.open(image_path).convert("RGB")
            tensor = self.transform(img).unsqueeze(0)  # (1, 3, 224, 224)

            with torch.no_grad():
                embed = self.model(tensor)

            return embed.squeeze(0).cpu().numpy().astype(np.float32)
        except Exception as e:
            logger.error("ResNet50 特征提取失败 %s: %s", image_path, str(e))
            return None

    def _extract_cv(self, image_path):
        """使用传统 CV 方法提取特征（降级方案）"""
        try:
            from PIL import Image, ImageFilter, ImageStat
            img = Image.open(image_path).convert("RGB")
            return self._compute_cv_features(img)
        except Exception as e:
            logger.error("CV 特征提取失败 %s: %s", image_path, str(e))
            return None

    def _compute_cv_features(self, img):
        """传统 CV 特征: pHash(64) + 颜色直方图(48) + 边缘纹理(16) = 128"""
        phash_vec = self._phash(img, size=8)
        color_vec = self._color_histogram(img)
        texture_vec = self._edge_texture(img)
        feature = np.concatenate([phash_vec, color_vec, texture_vec])
        feature = feature / (np.linalg.norm(feature) + 1e-8)
        return feature.astype(np.float32)

    def _phash(self, img, size=8):
        img_gray = img.convert("L").resize((32, 32), Image.LANCZOS)
        pixels = np.array(img_gray, dtype=np.float32)

        def dct_1d(x):
            N = len(x)
            result = np.zeros(N)
            for k in range(N):
                result[k] = np.sum(x * np.cos(np.pi * k * (np.arange(N) + 0.5) / N))
            return result

        dct_rows = np.apply_along_axis(dct_1d, 0, pixels)
        dct_2d = np.apply_along_axis(dct_1d, 1, dct_rows)
        dct_low = dct_2d[:size, :size]
        flat = dct_low.flatten()
        mean = np.mean(flat)
        bits = (flat > mean).astype(np.float32)
        return bits

    def _color_histogram(self, img):
        hist_feat = []
        for channel in img.split():
            hist = channel.histogram()
            hist_16 = np.array([sum(hist[i:i+16]) for i in range(0, 256, 16)], dtype=np.float32)
            hist_16 = hist_16 / (np.sum(hist_16) + 1e-8)
            hist_feat.append(hist_16)
        return np.concatenate(hist_feat)

    def _edge_texture(self, img):
        from PIL import ImageFilter
        img_gray = img.convert("L").resize((64, 64), Image.LANCZOS)
        edges = img_gray.filter(ImageFilter.FIND_EDGES)
        edge_arr = np.array(edges, dtype=np.float32)
        h, w = edge_arr.shape
        block_h, block_w = h // 4, w // 4
        texture = np.zeros(16, dtype=np.float32)
        for i in range(4):
            for j in range(4):
                block = edge_arr[i*block_h:(i+1)*block_h, j*block_w:(j+1)*block_w]
                texture[i*4 + j] = np.mean(block)
        texture = texture / (np.max(texture) + 1e-8)
        return texture

    def extract(self, image_paths, microscope_paths=None):
        """
        从多张图片融合提取特征（兼容旧接口）

        Returns:
            (dna_hash, feature_vector) 或 None
        """
        all_paths = list(image_paths)
        if microscope_paths:
            all_paths.extend(microscope_paths)
        if not all_paths:
            return None

        vectors = []
        for path in all_paths:
            vec = self.extract_single(path)
            if vec is not None:
                vectors.append(vec)

        if not vectors:
            return None

        fused = np.mean(vectors, axis=0)
        fused = fused / (np.linalg.norm(fused) + 1e-8)
        dna_hash = _vector_to_hash(fused)
        return dna_hash, fused


def _vector_to_hash(feature_vector):
    """特征向量 → SHA-256 哈希"""
    vec_str = ",".join(f"{v:.6f}" for v in feature_vector)
    return hashlib.sha256(vec_str.encode("utf-8")).hexdigest()


def compute_dhash(image_path, hash_size=8):
    """
    计算图像的感知哈希（dHash, 64 位）

    用于「识别具体是哪一件作品」的实例级身份匹配：
    - 同一张图（或几乎相同的图）→ 汉明距离极小，能精确区分不同作品
    - 相较 ResNet 通用特征，dHash 能清晰区分视觉上相近的不同作品

    Args:
        image_path: 图片文件路径

    Returns:
        64 位 '0'/'1' 字符串；失败返回 None
    """
    try:
        from PIL import Image
        img = Image.open(image_path).convert("L")
        img = img.resize((hash_size + 1, hash_size), Image.LANCZOS)
        pixels = np.asarray(img, dtype=np.float32)
        # 相邻列比较：左亮于右记为 1
        diff = pixels[:, 1:] > pixels[:, :-1]
        bits = diff.flatten().astype(np.uint8)
        return "".join(str(int(b)) for b in bits)
    except Exception as e:
        logger.error("dHash 计算失败 %s: %s", image_path, str(e))
        return None


def dhash_similarity(hash_a, hash_b):
    """
    计算两个 dHash 字符串的相似度，范围 0~1

    按「近重复」尺度归一化（汉明距离约 ≥16 即视为不同作品），
    使「识别具体是哪一件作品」时身份级区分更敏锐：
      - 完全相同 → 1.0
      - 视觉近似（距离<16）→ 0~1 之间的中间值
      - 明显不同（距离≥16）→ 0.0
    """
    if not hash_a or not hash_b or len(hash_a) != len(hash_b):
        return 0.0
    hamming = sum(1 for a, b in zip(hash_a, hash_b) if a != b)
    return max(0.0, 1.0 - hamming / 16.0)


def compare_feature_vectors(query_bytes, target_bytes, threshold=0.85):
    """
    比对两个特征向量，计算余弦相似度
    """
    try:
        query_vec = np.array(pickle.loads(query_bytes))
        target_vec = np.array(pickle.loads(target_bytes))
        similarity = float(np.dot(query_vec, target_vec))
        is_match = similarity >= threshold
        return similarity, is_match
    except Exception as e:
        logger.error("特征比对失败: %s", str(e))
        return 0.0, False


def warmup_model():
    """预热模型（兼容旧接口）"""
    return True