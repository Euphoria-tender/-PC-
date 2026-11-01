"""
文化DNA —— 非遗作品确权溯源系统
区块链存证模型：t_chain_record 表
"""
from app import db


class TChainRecord(db.Model):
    """区块链存证记录表，记录作品在Hyperledger Fabric上的存证信息"""
    __tablename__ = "t_chain_record"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键ID")
    work_id = db.Column(
        db.Integer,
        db.ForeignKey("t_artwork.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联作品ID"
    )
    certificate_no = db.Column(
        db.String(128),
        unique=True,
        nullable=False,
        index=True,
        comment="证书编号（唯一）"
    )
    tx_id = db.Column(db.String(256), nullable=False, comment="区块链交易ID")
    block_height = db.Column(db.BigInteger, nullable=False, comment="区块高度")
    chain_code = db.Column(
        db.String(64),
        nullable=False,
        comment="链码名称"
    )
    channel_name = db.Column(
        db.String(64),
        nullable=False,
        comment="Fabric通道名称"
    )
    status = db.Column(
        db.String(32),
        default="pending",
        comment="存证状态：pending（待上链）/ success（上链成功）/ failed（上链失败）"
    )
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        comment="存证时间"
    )

    # ── 关联关系 ────────────────────────────────────────────────
    artwork = db.relationship("TArtwork", back_populates="chain_records")

    def __repr__(self):
        return f"<TChainRecord certificate_no={self.certificate_no} tx_id={self.tx_id}>"