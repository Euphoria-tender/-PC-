"""
文化DNA —— 桌面版数据库初始化脚本
创建默认管理员账号和测试数据
"""
import os
import sys

# 确保导入路径正确
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import bcrypt
from config_desktop import DesktopConfig
from app import create_app, db
from app.models.user import TUser


def seed():
    """初始化数据库和默认账号"""
    app = create_app(config_name=None)
    app.config.from_object(DesktopConfig)

    with app.app_context():
        # 创建所有表
        db.create_all()
        print("数据库表已创建")

        # 检查是否已有管理员
        admin = TUser.query.filter_by(username="admin").first()
        if admin:
            print(f"管理员账号已存在: admin (ID: {admin.id})")
        else:
            admin = TUser(
                username="admin",
                password_hash=bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8"),
                role="admin",
                real_name="系统管理员",
                phone="13800000001",
                must_change_password=True,
            )
            db.session.add(admin)
            db.session.commit()
            print("默认管理员账号已创建: admin / admin123")

        # 创建一个测试用户
        test_user = TUser.query.filter_by(username="test").first()
        if not test_user:
            test_user = TUser(
                username="test",
                password_hash=bcrypt.hashpw("test123".encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8"),
                role="inheritor",
                real_name="测试传承人",
                phone="13800000002",
                must_change_password=False,
            )
            db.session.add(test_user)
            db.session.commit()
            print("测试用户已创建: test / test123")

        print("\n初始化完成！")
        print("=" * 40)
        print("管理员: admin / admin123")
        print("测试用户: test / test123")
        print("=" * 40)


if __name__ == "__main__":
    seed()