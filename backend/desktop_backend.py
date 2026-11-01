"""
文化DNA —— 桌面版后端入口
使用 SQLite 数据库，在 localhost:5500 上运行
"""
import os
import sys

# 确保当前目录在 Python 路径中
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from config_desktop import DesktopConfig
from app import create_app, db
from app.utils.logger import setup_logger
from flask import send_from_directory


def _seed_default_users(app):
    """创建默认管理员与测试账号（仅当不存在时）"""
    import bcrypt
    from app.models.user import TUser

    try:
        admin = TUser.query.filter_by(username="admin").first()
        if not admin:
            db.session.add(TUser(
                username="admin",
                password_hash=bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8"),
                role="admin",
                real_name="系统管理员",
                phone="13800000001",
                must_change_password=True,
            ))
            app.logger.info("已创建默认管理员: admin / admin123")

        test = TUser.query.filter_by(username="test").first()
        if not test:
            db.session.add(TUser(
                username="test",
                password_hash=bcrypt.hashpw("test123".encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8"),
                role="inheritor",
                real_name="测试传承人",
                phone="13800000002",
                must_change_password=False,
            ))
            app.logger.info("已创建测试账号: test / test123")

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.warning("默认账号初始化失败: %s", str(e))


def _get_seed_images_dir():
    """获取打包后的演示图片目录（开发环境 与 PyInstaller 冻结环境兼容）"""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "seed_images")
    return os.path.join(_BACKEND_DIR, "seed_images")


# ── 演示作品（8件视觉互异的非遗作品）──────────────────────────────
_DEMO_ARTWORKS = [
    {
        "title": "南京云锦织金妆花龙袍",
        "category": "刺绣",
        "image": "embroidery_yunjin.png",
        "description": "明代云锦织造工艺代表作，采用织金妆花技法，龙纹以金线织就，为皇室御用袍服。",
    },
    {
        "title": "粤绣九龙屏风",
        "category": "刺绣",
        "image": "embroidery_yuejiu.png",
        "description": "岭南粤绣代表作品，九龙腾云图案，运用盘金、钉金等传统粤绣针法绣制。",
    },
    {
        "title": "龙泉青瓷凤耳瓶",
        "category": "陶瓷",
        "image": "ceramic_longquan.png",
        "description": "南宋龙泉窑青瓷经典器型，凤耳瓶通体施梅子青釉，釉色温润如玉。",
    },
    {
        "title": "汝窑天青釉弦纹瓶",
        "category": "陶瓷",
        "image": "ceramic_ruyao.png",
        "description": "北宋汝窑天青釉代表器，釉面开片如冰裂，弦纹简洁典雅，世所罕见。",
    },
    {
        "title": "东阳木雕百子图",
        "category": "木雕",
        "image": "woodcarving_dongyang.png",
        "description": "浙江东阳木雕精品，百子嬉戏图，多层镂空雕刻，刀法细腻传神。",
    },
    {
        "title": "扬州剪纸百花图",
        "category": "剪纸",
        "image": "papercut_yangzhou.png",
        "description": "扬州剪纸传统作品，百花绽放图案，线条流畅，构图饱满富于韵律。",
    },
    {
        "title": "平遥推光漆仕女图屏风",
        "category": "漆器",
        "image": "lacquer_pingyao.png",
        "description": "山西平遥推光漆器代表作，仕女题材屏风，漆面推光后光亮如镜。",
    },
    {
        "title": "孟姜女传说",
        "category": "其他",
        "image": "other_mengjiangnv.png",
        "description": "国家级非物质文化遗产民间文学代表，孟姜女哭长城传说故事图。",
    },
]


def _migrate_schema(app):
    """轻量迁移：为已存在的旧库表补上新增列（桌面版不依赖 alembic）"""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)

    def _add_column(table, column, ddl):
        try:
            if table in inspector.get_table_names():
                cols = [c["name"] for c in inspector.get_columns(table)]
                if column not in cols:
                    with db.engine.begin() as conn:
                        conn.execute(text(ddl))
                    app.logger.info("已为 %s 增加 %s 列", table, column)
        except Exception as e:
            app.logger.warning("迁移 %s.%s 失败（可忽略）: %s", table, column, str(e))

    _add_column(
        "t_fingerprint", "perceptual_hash",
        "ALTER TABLE t_fingerprint ADD COLUMN perceptual_hash VARCHAR(128)"
    )
    _add_column(
        "t_artwork", "review_grade",
        "ALTER TABLE t_artwork ADD COLUMN review_grade VARCHAR(32)"
    )


def _seed_demo_artworks(app):
    """
    创建演示非遗作品并提取DNA指纹（仅当不存在作品时），
    使「AI 识别」功能开箱即用，能识别出「具体是哪一件作品」。
    """
    import shutil
    from app.models.artwork import TArtwork
    from app.models.fingerprint import TFingerprint
    from app.models.user import TUser
    from app.services.ai_service import extract_dna_features

    # 幂等：已有作品则跳过
    if TArtwork.query.count() > 0:
        return

    seed_dir = _get_seed_images_dir()
    upload_root = app.config.get("UPLOAD_FOLDER", os.path.join(_BACKEND_DIR, "uploads"))
    artworks_dir = os.path.join(upload_root, "artworks")
    os.makedirs(artworks_dir, exist_ok=True)

    owner = (
        TUser.query.filter_by(username="test").first()
        or TUser.query.filter_by(username="admin").first()
    )
    if not owner:
        app.logger.warning("演示作品初始化跳过：无可用归属账号")
        return

    created = 0
    try:
        for item in _DEMO_ARTWORKS:
            src = os.path.join(seed_dir, item["image"])
            if not os.path.exists(src):
                app.logger.warning("缺少演示图片，跳过: %s", item["image"])
                continue

            dst = os.path.join(artworks_dir, item["image"])
            if not os.path.exists(dst):
                shutil.copy2(src, dst)

            work = TArtwork(
                user_id=owner.id,
                title=item["title"],
                category=item["category"],
                description=item["description"],
                images=[f"/artworks/{item['image']}"],
                dna_status="processing",
                review_status="approved",
            )
            db.session.add(work)
            db.session.flush()  # 获取 work.id

            # 提取DNA指纹（CNN 特征 + 感知哈希）
            try:
                result = extract_dna_features([dst], [])
                if result:
                    dna_hash, feature_bytes, dhash_str = result
                    db.session.add(TFingerprint(
                        work_id=work.id,
                        dna_hash=dna_hash,
                        feature_vector=feature_bytes,
                        perceptual_hash=dhash_str,
                    ))
                    work.dna_status = "completed"
                    created += 1
            except Exception as e:
                app.logger.warning("作品「%s」DNA提取失败: %s", item["title"], str(e))
                work.dna_status = "failed"

        db.session.commit()
        app.logger.info("演示作品初始化完成，共 %d 件", created)
    except Exception as e:
        db.session.rollback()
        app.logger.warning("演示作品初始化失败: %s", str(e))


def create_desktop_app():
    """创建桌面版 Flask 应用实例"""
    # 直接传入 DesktopConfig，确保 db.init_app 时就用正确的数据库路径
    app = create_app(config_object=DesktopConfig)

    # 确保上传目录存在
    upload_folder = app.config.get("UPLOAD_FOLDER", os.path.join(_BACKEND_DIR, "uploads"))
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(os.path.join(upload_folder, "identify"), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, "verify"), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, "online_cache"), exist_ok=True)
    # 发布存证目录（IPFS 不可用时的本地离线存证落盘）
    os.makedirs(os.path.join(os.path.dirname(upload_folder), "published"), exist_ok=True)

    # 确保日志目录存在
    log_dir = os.path.join(_BACKEND_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)

    return app


# 创建应用实例
app = create_desktop_app()

# 初始化日志系统
setup_logger(app)


# 上传文件的静态访问路由（供前端预览作品图片）
@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# 自动初始化数据库表 + 创建默认账号 + 演示作品
with app.app_context():
    db.create_all()
    app.logger.info("数据库表已初始化")
    _migrate_schema(app)
    _seed_default_users(app)
    _seed_demo_artworks(app)


@app.shell_context_processor
def make_shell_context():
    """Flask Shell 上下文处理器"""
    from app.models import (
        TUser, TArtwork, TFingerprint,
        TChainRecord, TOwnershipTransfer, TVerificationLog,
        TReferenceImage, TPublishRecord
    )
    return {
        "db": db,
        "TUser": TUser,
        "TArtwork": TArtwork,
        "TFingerprint": TFingerprint,
        "TChainRecord": TChainRecord,
        "TOwnershipTransfer": TOwnershipTransfer,
        "TVerificationLog": TVerificationLog,
        "TReferenceImage": TReferenceImage,
        "TPublishRecord": TPublishRecord,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("文化DNA 桌面版后端启动中...")
    print(f"数据库: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"AI模型: {app.config['AI_MODEL_PATH']}")
    print(f"监听地址: http://localhost:5500")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5500, debug=False)