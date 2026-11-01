"""
文化DNA —— 非遗作品确权溯源系统
身份认证申请模型：t_role_application 表
"""
from app import db


class TRoleApplication(db.Model):
    """普通用户提交资料申请认证为传承人/鉴定师的身份申请表"""
    __tablename__ = "t_role_application"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键ID")
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("t_user.id", ondelete="CASCADE"),
        nullable=False,
        comment="申请人用户ID"
    )
    target_role = db.Column(
        db.String(32),
        nullable=False,
        comment="申请的目标身份：inheritor（传承人）/ appraiser（鉴定师）"
    )
    real_name = db.Column(db.String(64), nullable=False, comment="申请人真实姓名")
    phone = db.Column(db.String(32), nullable=True, comment="联系电话")
    materials = db.Column(db.Text, nullable=False, comment="申请资料说明（技艺/资质/传承谱系等）")
    status = db.Column(
        db.String(32),
        default="pending",
        comment="审核状态：pending（待审核）/ approved（已通过）/ rejected（已驳回）"
    )
    review_comment = db.Column(db.Text, nullable=True, comment="审核意见")
    reviewed_by = db.Column(
        db.Integer,
        db.ForeignKey("t_user.id", ondelete="SET NULL"),
        nullable=True,
        comment="审核人用户ID"
    )
    reviewed_at = db.Column(db.DateTime, nullable=True, comment="审核时间")
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        comment="申请时间"
    )
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        comment="更新时间"
    )

    # ── 关联关系 ────────────────────────────────────────────────
    applicant = db.relationship("TUser", foreign_keys=[user_id])
    reviewer = db.relationship("TUser", foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<TRoleApplication id={self.id} target={self.target_role} status={self.status}>"