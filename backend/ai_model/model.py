"""
文化DNA —— 非遗作品确权溯源系统
AI模型定义模块
基于 torchvision ResNet50 预训练模型，输出128维特征向量用于作品DNA指纹提取
"""
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import resnet50, ResNet50_Weights
from typing import Optional, Tuple


class CulturalDNAModel(nn.Module):
    """
    文化DNA特征提取模型

    架构：
    - 主干网络：ResNet50（ImageNet预训练，去掉最后的全连接层）
    - 特征投影：2048 → 512 → 128（含BatchNorm + ReLU）
    - 输出层：L2归一化的128维特征向量

    用途：
    - 从非遗作品图片中提取视觉DNA指纹
    - 128维特征向量用于余弦相似度比对
    """

    def __init__(self, pretrained: bool = True, freeze_backbone: bool = False):
        """
        初始化模型

        Args:
            pretrained: 是否加载ImageNet预训练权重（默认True）
            freeze_backbone: 是否冻结主干网络参数（默认False，允许微调）
        """
        super(CulturalDNAModel, self).__init__()

        # ── 主干网络：ResNet50（去掉最后的全连接层） ──────────────
        if pretrained:
            resnet = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
        else:
            resnet = resnet50(weights=None)

        # 提取ResNet50的特征提取部分（去掉最后的fc层）
        self.backbone = nn.Sequential(
            resnet.conv1,      # 7x7卷积, stride=2
            resnet.bn1,        # BatchNorm
            resnet.relu,       # ReLU
            resnet.maxpool,    # 3x3最大池化
            resnet.layer1,     # Bottleneck x3, 输出256通道
            resnet.layer2,     # Bottleneck x4, 输出512通道
            resnet.layer3,     # Bottleneck x6, 输出1024通道
            resnet.layer4,     # Bottleneck x3, 输出2048通道
        )
        self.backbone_out_channels = 2048  # ResNet50 layer4 输出通道数

        # 可选：冻结主干网络
        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False

        # ── 全局平均池化 ────────────────────────────────────────
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))

        # ── 特征投影头：2048 → 512 → 128 ─────────────────────────
        self.projection = nn.Sequential(
            nn.Linear(2048, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3),
            nn.Linear(512, 128),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播

        Args:
            x: 输入图像张量，形状 (batch_size, 3, 224, 224)

        Returns:
            L2归一化后的128维特征向量，形状 (batch_size, 128)
        """
        # 主干网络提取特征
        features = self.backbone(x)          # (B, 2048, 7, 7)

        # 全局平均池化
        features = self.global_pool(features)  # (B, 2048, 1, 1)
        features = torch.flatten(features, 1)  # (B, 2048)

        # 投影到128维
        embedding = self.projection(features)  # (B, 128)

        # L2归一化，使特征向量单位化（便于余弦相似度计算）
        embedding = F.normalize(embedding, p=2, dim=1)

        return embedding


# ── 模型加载与保存 ────────────────────────────────────────────────

def load_model(
    checkpoint_path: Optional[str] = None,
    device: Optional[str] = None,
    pretrained: bool = True,
) -> Tuple[nn.Module, torch.device]:
    """
    加载模型（支持从checkpoint恢复）

    加载优先级：
    1. 如果 checkpoint_path 存在，加载训练好的权重
    2. 否则使用 ImageNet 预训练权重（初始状态）

    Args:
        checkpoint_path: 模型权重文件路径（.pth），为None则使用预训练权重
        device: 指定设备（"cuda" / "cpu"），为None则自动检测
        pretrained: 是否加载ImageNet预训练权重

    Returns:
        (model, device) 元组
        model: 已加载权重的模型实例（eval模式）
        device: 实际使用的设备
    """
    # 自动检测设备
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    device = torch.device(device)

    # 创建模型实例
    model = CulturalDNAModel(pretrained=pretrained)

    # 加载checkpoint（如果提供且存在）
    if checkpoint_path and os.path.exists(checkpoint_path):
        try:
            checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
            # 兼容两种保存格式：完整模型 或 仅state_dict
            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                model.load_state_dict(checkpoint["model_state_dict"])
            elif isinstance(checkpoint, dict):
                model.load_state_dict(checkpoint)
            else:
                model = checkpoint
        except Exception as e:
            print(f"[AI Model] 加载checkpoint失败: {e}，使用初始权重")

    model = model.to(device)
    model.eval()  # 切换到评估模式

    return model, device


def save_model(model: nn.Module, checkpoint_path: str, metadata: Optional[dict] = None) -> None:
    """
    保存模型权重

    Args:
        model: 模型实例
        checkpoint_path: 保存路径（.pth）
        metadata: 额外的元数据（如训练轮次、准确率等）
    """
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "model_arch": "resnet50_cultural_dna",
        "feature_dim": 128,
    }
    if metadata:
        checkpoint.update(metadata)

    torch.save(checkpoint, checkpoint_path)
    print(f"[AI Model] 模型已保存至: {checkpoint_path}")


def get_device_info(device: torch.device) -> dict:
    """
    获取设备信息，用于调试和日志

    Args:
        device: PyTorch设备对象

    Returns:
        设备信息字典
    """
    info = {
        "device_type": device.type,
        "cuda_available": torch.cuda.is_available(),
    }
    if device.type == "cuda":
        info.update({
            "cuda_device_count": torch.cuda.device_count(),
            "cuda_device_name": torch.cuda.get_device_name(device),
            "cuda_memory_allocated": f"{torch.cuda.memory_allocated(device) / 1024**2:.1f} MB",
        })
    return info