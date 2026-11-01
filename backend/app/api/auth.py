"""
文化DNA —— 非遗作品确权溯源系统
认证模块 API 路由
实现用户登录、注册、个人信息管理
"""
import bcrypt
import requests
from flask import Blueprint, request, g, current_app
from app import db
from app.models.user import TUser
from app.utils.response import success_response, error_response
from app.utils.jwt_utils import generate_token, decode_token
from app.utils.auth_decorator import token_required

auth_bp = Blueprint("auth", __name__)


# ── 用户登录 ────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    用户登录接口

    请求体: { "username": "xxx", "password": "xxx" }
    成功返回: { "code": 0, "data": { "access_token": "...", "user": {...} } }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return error_response("用户名和密码不能为空", 400)

        # 查询用户
        user = TUser.query.filter_by(username=username).first()
        if not user:
            return error_response("用户名或密码错误", 401)

        # 验证密码
        try:
            is_valid = bcrypt.checkpw(
                password.encode("utf-8"),
                user.password_hash.encode("utf-8")
            )
        except (ValueError, TypeError):
            return error_response("用户名或密码错误", 401)

        if not is_valid:
            return error_response("用户名或密码错误", 401)

        # 生成JWT令牌
        access_token = generate_token(user.id, user.role, token_type="access")
        refresh_token = generate_token(user.id, user.role, token_type="refresh")

        return success_response({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "real_name": user.real_name,
                "phone": user.phone,
            },
            "must_change_password": user.must_change_password,
        }, "登录成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"登录失败: {str(e)}", 500)


# ── 用户注册 ────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    传承人注册接口

    请求体: {
        "username": "xxx",
        "password": "xxx",
        "real_name": "xxx",
        "phone": "xxx",
        "role": "inheritor"   // 可选，默认 inheritor
    }
    成功返回: { "code": 0, "data": { "user_id": 1 } }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        username = data.get("username", "").strip()
        password = data.get("password", "")
        real_name = data.get("real_name", "").strip()
        phone = data.get("phone", "").strip()
        role = data.get("role", "inheritor").strip()

        # 参数校验
        if not username or len(username) < 3:
            return error_response("用户名至少需要3个字符", 400)
        if not password or len(password) < 6:
            return error_response("密码至少需要6个字符", 400)
        if not real_name:
            return error_response("真实姓名不能为空", 400)

        # 允许的角色
        allowed_roles = ("inheritor", "appraiser", "user")
        if role not in allowed_roles:
            return error_response(f"无效的角色，允许: {', '.join(allowed_roles)}", 400)

        # 检查用户名唯一性
        existing = TUser.query.filter_by(username=username).first()
        if existing:
            return error_response("用户名已被注册", 409)

        # 密码哈希
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        # 创建用户
        new_user = TUser(
            username=username,
            password_hash=password_hash,
            role=role,
            real_name=real_name,
            phone=phone,
        )
        db.session.add(new_user)
        db.session.commit()

        return success_response({
            "user_id": new_user.id,
            "username": new_user.username,
            "role": new_user.role,
        }, "注册成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"注册失败: {str(e)}", 500)


# ── 获取当前用户信息 ────────────────────────────────────────────
@auth_bp.route("/profile", methods=["GET"])
@token_required
def profile():
    """
    获取当前登录用户信息（需认证）

    请求头: Authorization: Bearer <token>
    返回: { "code": 0, "data": { "user": {...} } }
    """
    try:
        user_id = g.current_user["user_id"]
        user = db.session.get(TUser, user_id)

        if not user:
            return error_response("用户不存在", 404)

        return success_response({
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "real_name": user.real_name,
                "phone": user.phone,
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else None,
            }
        })

    except Exception as e:
        return error_response(f"获取用户信息失败: {str(e)}", 500)


# ── 修改密码 ────────────────────────────────────────────────────
@auth_bp.route("/change-password", methods=["PUT"])
@token_required
def change_password():
    """
    修改密码（需认证）

    请求体: { "old_password": "xxx", "new_password": "xxx" }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        old_password = data.get("old_password", "")
        new_password = data.get("new_password", "")

        if not old_password or not new_password:
            return error_response("旧密码和新密码不能为空", 400)
        if len(new_password) < 6:
            return error_response("新密码至少需要6个字符", 400)

        user = db.session.get(TUser, g.current_user["user_id"])
        if not user:
            return error_response("用户不存在", 404)

        # 验证旧密码
        try:
            is_valid = bcrypt.checkpw(
                old_password.encode("utf-8"),
                user.password_hash.encode("utf-8")
            )
        except (ValueError, TypeError):
            return error_response("旧密码错误", 401)

        if not is_valid:
            return error_response("旧密码错误", 401)

        # 更新密码
        user.password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")
        # 清除「首次登录强制改密码」标志
        user.must_change_password = False
        db.session.commit()

        return success_response(message="密码修改成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"修改密码失败: {str(e)}", 500)


# ── 刷新令牌 ────────────────────────────────────────────────────
@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """
    刷新JWT令牌

    请求体: { "refresh_token": "xxx" }
    返回: { "code": 0, "data": { "access_token": "...", "refresh_token": "..." } }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        refresh_token_str = data.get("refresh_token", "")
        if not refresh_token_str:
            return error_response("refresh_token不能为空", 400)

        # 验证refresh token
        payload = decode_token(refresh_token_str)
        if payload is None:
            return error_response("refresh_token无效或已过期", 401)
        if payload.get("type") != "refresh":
            return error_response("令牌类型错误", 401)

        user_id = payload.get("user_id")

        # 验证用户仍存在
        user = db.session.get(TUser, user_id)
        if not user:
            return error_response("用户不存在", 404)

        # 生成新令牌（角色以数据库为准，避免角色被修改后刷新令牌仍沿用旧角色）
        new_access_token = generate_token(user.id, user.role, token_type="access")
        new_refresh_token = generate_token(user.id, user.role, token_type="refresh")

        return success_response({
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        }, "令牌刷新成功")

    except Exception as e:
        return error_response(f"刷新令牌失败: {str(e)}", 500)


# ── 微信小程序登录 ────────────────────────────────────────────
@auth_bp.route("/wechat-login", methods=["POST"])
def wechat_login():
    """
    微信小程序登录接口

    请求体: { "code": "wx.login()返回的临时code" }
    流程:
        1. 用 code 换取 openid
        2. 查找或创建用户
        3. 返回 JWT 令牌

    返回: { "code": 0, "data": { "access_token": "...", "user": {...} } }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        code = data.get("code", "").strip()
        if not code:
            return error_response("code不能为空", 400)

        appid = current_app.config.get("WECHAT_APPID", "")
        secret = current_app.config.get("WECHAT_SECRET", "")

        if not appid or not secret:
            return error_response("微信小程序配置未设置，请联系管理员", 500)

        # 调用微信接口换取 openid
        wx_url = (
            "https://api.weixin.qq.com/sns/jscode2session"
            f"?appid={appid}&secret={secret}&js_code={code}"
            "&grant_type=authorization_code"
        )

        try:
            wx_resp = requests.get(wx_url, timeout=10)
            wx_data = wx_resp.json()
        except requests.RequestException:
            return error_response("微信服务暂时不可用，请稍后再试", 502)

        if "errcode" in wx_data and wx_data["errcode"] != 0:
            return error_response(f"微信登录失败: {wx_data.get('errmsg', '未知错误')}", 401)

        openid = wx_data.get("openid")
        unionid = wx_data.get("unionid")  # 需要绑定开放平台才有

        if not openid:
            return error_response("获取openid失败", 500)

        # 查找或创建用户
        user = TUser.query.filter_by(openid=openid).first()
        is_new_user = False

        if not user:
            # 自动创建新用户
            username = f"wx_{openid[-8:]}"
            user = TUser(
                username=username,
                password_hash="",  # 微信登录用户无密码
                role="user",
                real_name="微信用户",
                openid=openid,
                unionid=unionid,
            )
            db.session.add(user)
            db.session.commit()
            is_new_user = True

        # 更新 unionid（如果有）
        if unionid and not user.unionid:
            user.unionid = unionid
            db.session.commit()

        # 生成 JWT
        access_token = generate_token(user.id, user.role, token_type="access")
        refresh_token = generate_token(user.id, user.role, token_type="refresh")

        return success_response({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "real_name": user.real_name,
                "phone": user.phone,
            },
            "is_new_user": is_new_user,
        }, "登录成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"微信登录失败: {str(e)}", 500)


# ── 绑定微信 ──────────────────────────────────────────────────
@auth_bp.route("/wechat-bind", methods=["PUT"])
@token_required
def wechat_bind():
    """
    将当前登录用户绑定微信 openid

    请求体: { "code": "wx.login()返回的临时code" }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return error_response("请求体不能为空", 400)

        code = data.get("code", "").strip()
        if not code:
            return error_response("code不能为空", 400)

        appid = current_app.config.get("WECHAT_APPID", "")
        secret = current_app.config.get("WECHAT_SECRET", "")

        if not appid or not secret:
            return error_response("微信小程序配置未设置", 500)

        wx_url = (
            "https://api.weixin.qq.com/sns/jscode2session"
            f"?appid={appid}&secret={secret}&js_code={code}"
            "&grant_type=authorization_code"
        )

        try:
            wx_resp = requests.get(wx_url, timeout=10)
            wx_data = wx_resp.json()
        except requests.RequestException:
            return error_response("微信服务暂时不可用", 502)

        if "errcode" in wx_data and wx_data["errcode"] != 0:
            return error_response(f"微信登录失败: {wx_data.get('errmsg', '未知错误')}", 401)

        openid = wx_data.get("openid")
        if not openid:
            return error_response("获取openid失败", 500)

        # 检查 openid 是否已被其他用户绑定
        existing = TUser.query.filter_by(openid=openid).first()
        if existing and existing.id != g.current_user["user_id"]:
            return error_response("该微信已绑定其他账号", 409)

        user = db.session.get(TUser, g.current_user["user_id"])
        if not user:
            return error_response("用户不存在", 404)

        user.openid = openid
        if wx_data.get("unionid"):
            user.unionid = wx_data["unionid"]
        db.session.commit()

        return success_response(message="微信绑定成功")

    except Exception as e:
        db.session.rollback()
        return error_response(f"绑定失败: {str(e)}", 500)