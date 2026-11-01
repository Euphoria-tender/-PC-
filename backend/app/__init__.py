"""
文化DNA —— 非遗作品确权溯源系统
Flask 应用工厂模块
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from config import config_map

# ── 全局扩展实例 ────────────────────────────────────────────────
# SQLAlchemy 和 Migrate 在工厂函数中初始化，此处声明为全局变量
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name: str = None, config_object=None) -> Flask:
    """
    应用工厂函数，根据配置名称创建 Flask 应用实例

    Args:
        config_name: 配置名称（development / production / testing），
                     默认从环境变量 FLASK_ENV 读取，未设置则使用 development

    Returns:
        Flask 应用实例
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)

    # ── 加载配置（优先使用传入的 config_object，否则按名称加载）───
    if config_object is not None:
        app.config.from_object(config_object)
    else:
        app.config.from_object(config_map[config_name])

    # ── 初始化扩展 ──────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # ── 注册蓝图 ────────────────────────────────────────────────
    # 蓝图延迟导入，避免循环依赖
    from app.api.auth import auth_bp
    from app.api.works import works_bp
    from app.api.certificates import certificates_bp
    from app.api.trace import trace_bp
    from app.api.statistics import statistics_bp
    from app.api.admin import admin_bp
    from app.api.identify import identify_bp
    from app.api.references import references_bp
    from app.api.publish import publish_bp
    from app.api.certification import certification_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(works_bp, url_prefix="/api/works")
    app.register_blueprint(certificates_bp, url_prefix="/api/certificates")
    app.register_blueprint(trace_bp, url_prefix="/api/trace")
    app.register_blueprint(statistics_bp, url_prefix="/api/statistics")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(identify_bp, url_prefix="/api")
    app.register_blueprint(references_bp, url_prefix="/api/references")
    app.register_blueprint(publish_bp, url_prefix="/api/publish")
    app.register_blueprint(certification_bp, url_prefix="/api/certification")

    # ── 注册全局错误处理 ────────────────────────────────────────
    register_error_handlers(app)

    # ── AI模型预热（后台线程异步加载，不阻塞 Flask 启动） ────────
    def _warmup_in_background():
        import time
        time.sleep(1)  # 等 Flask 启动完成后再加载
        try:
            from app.services.ai_service import warmup_model
            with app.app_context():
                warmup_model()
        except Exception as e:
            app.logger.warning("AI模型预热失败（将在首次请求时加载）: %s", str(e))

    import threading
    threading.Thread(target=_warmup_in_background, daemon=True).start()

    return app


def register_error_handlers(app: Flask) -> None:
    """
    注册全局 HTTP 异常处理器，统一返回JSON格式

    Args:
        app: Flask 应用实例
    """
    from app.utils.response import error_response

    @app.errorhandler(400)
    def bad_request(e):
        return error_response("请求参数错误", 400)

    @app.errorhandler(401)
    def unauthorized(e):
        return error_response("未授权，请先登录", 401)

    @app.errorhandler(403)
    def forbidden(e):
        return error_response("权限不足", 403)

    @app.errorhandler(404)
    def not_found(e):
        return error_response("资源不存在", 404)

    @app.errorhandler(405)
    def method_not_allowed(e):
        return error_response("请求方法不允许", 405)

    @app.errorhandler(500)
    def internal_error(e):
        return error_response("服务器内部错误", 500)