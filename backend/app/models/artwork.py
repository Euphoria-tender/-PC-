"""
文化DNA —— 非遗作品确权溯源系统
作品模型：t_artwork 表
"""
import uuid
from app import db


class TArtwork(db.Model):
    """非遗作品表，记录作品基本信息及DNA提取状态"""
    __tablename__ = "t_artwork"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键ID")
    work_id = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
        comment="作品唯一编号（UUID）"
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("t_user.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属用户ID"
    )
    title = db.Column(db.String(256), nullable=False, comment="作品名称")
    category = db.Column(
        db.String(64),
        nullable=False,
        comment="作品类别：刺绣 / 陶瓷 / 木雕 / 剪纸 / 漆器 / 其他"
    )
    description = db.Column(db.Text, comment="作品描述")
    images = db.Column(db.JSON, comment="作品图片URL列表（JSON数组）")
    microscope_images = db.Column(db.JSON, comment="微观图像URL列表（JSON数组）")
    dna_status = db.Column(
        db.String(32),
        default="pending",
        comment="DNA提取状态：pending（待提取）/ processing（提取中）/ completed（已完成）/ failed（失败）"
    )
    review_status = db.Column(
        db.String(32),
        default="pending",
        comment="审核状态：pending（待审核）/ approved（已通过）/ rejected（已驳回）"
    )
    review_comment = db.Column(
        db.Text,
        nullable=True,
        comment="审核意见"
    )
    review_grade = db.Column(
        db.String(32),
        nullable=True,
        comment="专家评级：master（大师级）/ premium（精品级）/ excellent（优良级）/ qualified（合格级）"
    )
    reviewed_by = db.Column(
        db.Integer,
        db.ForeignKey("t_user.id", ondelete="SET NULL"),
        nullable=True,
        comment="审核人用户ID"
    )
    reviewed_at = db.Column(
        db.DateTime,
        nullable=True,
        comment="审核时间"
    )
    source_url = db.Column(
        db.String(1024),
        nullable=True,
        comment="来源数据库URL（如Met Museum/WikiData/ihchina详情页）"
    )
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        comment="创建时间"
    )
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        comment="更新时间"
    )

    # ── 关联关系 ────────────────────────────────────────────────
    owner = db.relationship("TUser", back_populates="artworks", foreign_keys=[user_id])
    reviewer = db.relationship("TUser", back_populates="reviewed_artworks", foreign_keys=[reviewed_by])
    fingerprint = db.relationship(
        "TFingerprint",
        back_populates="artwork",
        uselist=False,
        cascade="all, delete-orphan"
    )
    chain_records = db.relationship(
        "TChainRecord",
        back_populates="artwork",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    ownership_transfers = db.relationship(
        "TOwnershipTransfer",
        back_populates="artwork",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    verification_logs = db.relationship(
        "TVerificationLog",
        back_populates="artwork",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    publish_records = db.relationship(
        "TPublishRecord",
        back_populates="artwork",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<TArtwork work_id={self.work_id} title={self.title}>"