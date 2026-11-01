"""
文化DNA —— 非遗作品确权溯源系统
鉴定日志模型：t_verification_log 表
"""
from app import db


class TVerificationLog(db.Model):
    """鉴定日志表，记录每次AI鉴定及DNA比对的详细结果"""
    __tablename__ = "t_verification_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键ID")
    work_id = db.Column(
        db.Integer,
        db.ForeignKey("t_artwork.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联作品ID"
    )
    verification_type = db.Column(
        db.String(32),
        nullable=False,
        comment="鉴定类型：ai_visual（AI视觉相似度）/ dna_match（DNA指纹比对）/ full（完整鉴定）"
    )
    ai_match_score = db.Column(
        db.DECIMAL(5, 4),
        comment="AI匹配得分（0.0000 ~ 1.0000），保留4位小数"
    )
    dna_verified = db.Column(
        db.Boolean,
        comment="DNA比对是否通过"
    )
    final_result = db.Column(
        db.String(32),
        nullable=False,
        comment="最终鉴定结果：authentic（真品）/ suspicious（存疑）/ counterfeit（赝品）"
    )
    response_time_ms = db.Column(
        db.Integer,
        comment="鉴定响应时间（毫秒）"
    )
    ip_address = db.Column(
        db.String(64),
        comment="请求来源IP地址"
    )
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        comment="鉴定时间"
    )

    # ── 关联关系 ────────────────────────────────────────────────
    artwork = db.relationship("TArtwork", back_populates="verification_logs")

    def __repr__(self):
        return f"<TVerificationLog id={self.id} work_id={self.work_id} final_result={self.final_result}>"