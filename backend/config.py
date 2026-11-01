"""
文化DNA —— 桌面版配置（兼容模块）
"""
import os
from datetime import timedelta


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get("SECRET_KEY", "cultural-dna-desktop-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.path.dirname(__file__), 'cultural_dna.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "cultural-dna-desktop-jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=90)
    IPFS_HOST = os.environ.get("IPFS_HOST", "127.0.0.1")
    IPFS_PORT = int(os.environ.get("IPFS_PORT", "5001"))
    FABRIC_NETWORK_CONFIG = os.environ.get("FABRIC_NETWORK_CONFIG", "")
    FABRIC_CHANNEL = os.environ.get("FABRIC_CHANNEL", "culturaldnachannel")
    FABRIC_CHAINCODE = os.environ.get("FABRIC_CHAINCODE", "artworkcc")
    FABRIC_OFFLINE_MODE = os.environ.get("FABRIC_OFFLINE_MODE", "true").lower() == "true"
    AI_MODEL_PATH = os.environ.get(
        "AI_MODEL_PATH",
        os.path.join(os.path.dirname(__file__), "ai_model", "checkpoints", "best.pth")
    )
    AI_MATCH_THRESHOLD = float(os.environ.get("AI_MATCH_THRESHOLD", "0.85"))
    WECHAT_APPID = os.environ.get("WECHAT_APPID", "")
    WECHAT_SECRET = os.environ.get("WECHAT_SECRET", "")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(os.path.dirname(__file__), "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE", os.path.join(os.path.dirname(__file__), "logs", "app.log"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}