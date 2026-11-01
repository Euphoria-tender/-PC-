"""
文化DNA —— 非遗作品确权溯源系统
指纹模型：t_fingerprint 表
记录AI提取的DNA哈希值和特征向量
"""
from app import db


class TFingerprint(db.Model):
    """DNA指纹表，存储作品AI特征提取结果，与作品一一对应"""
    __tablename__ = "t_fingerprint"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键ID")
    work_id = db.Column(
        db.Integer,
        db.ForeignKey("t_artwork.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="关联作品ID（一对一）"
    )
    dna_hash = db.Column(db.String(256), nullable=False, comment="DNA哈希值（SHA-256）")
    feature_vector = db.Column(
        db.LargeBinary,
        nullable=False,
        comment="特征向量（PyTorch Tensor 序列化后的二进制数据）"
    )
    perceptual_hash = db.Column(
        db.String(128),
        nullable=True,
        comment="感知哈希（dHash 64位字符串，用于实例级身份识别）"
    )
    extracted_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        comment="特征提取时间"
    )

    # ── 关联关系 ────────────────────────────────────────────────
    artwork = db.relationship("TArtwork", back_populates="fingerprint")

    def __repr__(self):
        return f"<TFingerprint id={self.id} work_id={self.work_id}>"