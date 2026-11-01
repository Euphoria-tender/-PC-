"""
文化DNA —— 非遗作品确权溯源系统
发布/同步台账模型：t_publish_record 表
记录作品「上传到网络」的存证结果（IPFS CID 或本地离线存证哈希），支持溯源。
"""
from app import db


class TPublishRecord(db.Model):
    """网络发布/同步台账表，记录每次「上传到网络」的存证"""
    __tablename__ = "t_publish_record"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键ID")
    work_id = db.Column(
        db.Integer,
        db.ForeignKey("t_artwork.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联作品ID"
    )
    publish_type = db.Column(
        db.String(32),
        nullable=False,
        comment="发布方式：ipfs（IPFS网络）/ local（本地离线存证）"
    )
    cid = db.Column(
        db.String(256),
        nullable=False,
        index=True,
        comment="内容寻址标识（IPFS CID 或本地 SHA-256 存证ID）"
    )
    resource_url = db.Column(
        db.String(1024),
        nullable=True,
        comment="可访问地址（ipfs://CID 或本地文件路径）"
    )
    payload = db.Column(
        db.JSON,
        nullable=True,
        comment="发布内容快照（作品元数据 + DNA哈希）"
    )
    status = db.Column(
        db.String(32),
        default="success",
        comment="发布状态：success（成功）/ failed（失败）"
    )
    message = db.Column(db.String(512), nullable=True, comment="发布说明")
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        comment="发布时间"
    )

    # ── 关联关系 ────────────────────────────────────────────────
    artwork = db.relationship("TArtwork", back_populates="publish_records")

    def __repr__(self):
        return f"<TPublishRecord id={self.id} type={self.publish_type} cid={self.cid}>"