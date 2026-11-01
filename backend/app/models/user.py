"""
文化DNA —— 非遗作品确权溯源系统
用户模型：t_user 表
"""
from app import db


class TUser(db.Model):
    """系统用户表，记录管理员、非遗传承人、鉴定师等角色"""
    __tablename__ = "t_user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键ID")
    username = db.Column(db.String(64), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = db.Column(db.String(256), nullable=False, comment="密码哈希值（bcrypt）")
    role = db.Column(
        db.String(32),
        nullable=False,
        default="user",
        comment="用户角色：admin（管理员）/ inheritor（传承人）/ appraiser（鉴定师）/ user（普通用户）"
    )
    real_name = db.Column(db.String(64), comment="真实姓名")
    phone = db.Column(db.String(20), comment="手机号码")
    openid = db.Column(
        db.String(128),
        unique=True,
        nullable=True,
        index=True,
        comment="微信OpenID（小程序登录绑定）"
    )
    unionid = db.Column(
        db.String(128),
        nullable=True,
        comment="微信UnionID"
    )
    must_change_password = db.Column(
        db.Boolean,
        default=False,
        comment="是否强制修改密码（首次登录标记）"
    )
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        comment="创建时间"
    )

    # ── 关联关系 ────────────────────────────────────────────────
    artworks = db.relationship(
        "TArtwork",
        back_populates="owner",
        lazy="dynamic",
        foreign_keys="TArtwork.user_id",
        cascade="all, delete-orphan"
    )
    reviewed_artworks = db.relationship(
        "TArtwork",
        back_populates="reviewer",
        lazy="dynamic",
        foreign_keys="TArtwork.reviewed_by"
    )

    def __repr__(self):
        return f"<TUser id={self.id} username={self.username} role={self.role}>"