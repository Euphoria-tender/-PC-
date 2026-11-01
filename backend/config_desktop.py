"""
文化DNA —— 桌面版后端配置
SQLite 数据库 + 离线模式
"""
import os
import sys
from datetime import timedelta

# 确保 ai_model 可以被导入
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


def _get_data_dir():
    """
    获取持久化数据目录（用户数据目录，而非 PyInstaller 临时解压目录）
    Windows: %APPDATA%/CulturalDNA
    """
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    data_dir = os.path.join(base, "CulturalDNA")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


class DesktopConfig:
    """桌面版配置类"""

    # ── Flask 核心配置 ──────────────────────────────────────────
    SECRET_KEY = "cultural-dna-desktop-secret-key-2026"

    # ── 数据库配置（SQLite，持久化到用户数据目录）─────────────────
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(_get_data_dir(), 'cultural_dna.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT 配置 ────────────────────────────────────────────────
    JWT_SECRET_KEY = "cultural-dna-desktop-jwt-secret-2026"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)      # 桌面版延长至24小时
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=90)      # 桌面版延长至90天

    # ── IPFS 配置（桌面版离线模式）─────────────────────────────────
    IPFS_HOST = "127.0.0.1"
    IPFS_PORT = 5001

    # ── Hyperledger Fabric 配置（桌面版离线模式）───────────────────
    FABRIC_NETWORK_CONFIG = ""
    FABRIC_CHANNEL = "culturaldnachannel"
    FABRIC_CHAINCODE = "artworkcc"
    FABRIC_OFFLINE_MODE = True

    # ── AI 模型配置 ─────────────────────────────────────────────
    AI_MODEL_PATH = os.environ.get(
        "AI_MODEL_PATH",
        os.path.join(_BACKEND_DIR, "ai_model", "checkpoints", "best.pth")
    )
    AI_MATCH_THRESHOLD = 0.85

    # ── 微信小程序配置（桌面版不需要）──────────────────────────────
    WECHAT_APPID = ""
    WECHAT_SECRET = ""

    # ── 上传文件配置（持久化到用户数据目录）───────────────────────
    UPLOAD_FOLDER = os.path.join(_get_data_dir(), "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # ── 日志配置（持久化到用户数据目录）───────────────────────────
    LOG_LEVEL = "INFO"
    LOG_FILE = os.path.join(_get_data_dir(), "logs", "app.log")
    DEBUG = False