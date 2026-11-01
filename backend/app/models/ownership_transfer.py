"""
文化DNA —— 非遗作品确权溯源系统
所有权转让模型：t_ownership_transfer 表
"""
from app import db


class TOwnershipTransfer(db.Model):
    """作品所有权转让记录表，记录每一次权属变更"""
    __tablename__ = "t_ownership_transfer"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键ID")
    work_id = db.Column(
        db.Integer,
        db.ForeignKey("t_artwork.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联作品ID"
    )
    from_owner = db.Column(
        db.Integer,
        nullable=False,
        comment="转让方用户ID"
    )
    to_owner = db.Column(
        db.Integer,
        nullable=False,
        comment="受让方用户ID"
    )
    tx_id = db.Column(db.String(256), nullable=False, comment="区块链交易ID")
    transferred_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        comment="转让时间"
    )

    # ── 关联关系 ────────────────────────────────────────────────
    artwork = db.relationship("TArtwork", back_populates="ownership_transfers")

    def __repr__(self):
        return f"<TOwnershipTransfer id={self.id} from_owner={self.from_owner} to_owner={self.to_owner}>"