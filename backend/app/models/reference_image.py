"""
文化DNA —— 非遗作品确权溯源系统
联网参考图库模型：t_reference_image 表
记录联网搜索下载的参考作品图片及其 DNA 特征，构成可检索、随检索自动扩充的本地图库。
"""
from app import db


class TReferenceImage(db.Model):
    """联网参考图库表，持久化联网搜索到的参考图片及其特征向量"""
    __tablename__ = "t_reference_image"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键ID")
    source = db.Column(
        db.String(32),
        nullable=False,
        default="bing",
        index=True,
        comment="图片来源：bing"
    )
    search_query = db.Column(
        db.String(256),
        nullable=False,
        index=True,
        comment="搜索关键词"
    )
    title = db.Column(db.String(512), nullable=True, comment="图片标题")
    image_url = db.Column(
        db.String(1024),
        nullable=False,
        comment="本地相对路径（uploads 目录下，如 /online_cache/xxx.jpg）"
    )
    source_url = db.Column(
        db.String(1024),
        nullable=False,
        comment="原始图片URL（第三方CDN，用于去重）"
    )
    perceptual_hash = db.Column(
        db.String(128),
        nullable=True,
        comment="感知哈希（dHash 64位字符串）"
    )
    feature_vector = db.Column(
        db.LargeBinary,
        nullable=True,
        comment="特征向量（pickle 序列化后的 numpy 数组，L2 归一化）"
    )
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        comment="入库时间"
    )

    def __repr__(self):
        return f"<TReferenceImage id={self.id} source={self.source} search_query={self.search_query}>"