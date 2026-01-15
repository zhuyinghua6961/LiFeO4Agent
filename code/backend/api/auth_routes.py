"""
认证API路由
登录、注册、获取用户信息、修改密码
"""
import logging
from flask import Blueprint, request, jsonify
from functools import wraps
from backend.services.auth_service import auth_service

logger = logging.getLogger(__name__)

# 创建蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def require_auth(f):
    """
    JWT认证装饰器
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # 获取Authorization头
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                "success": False,
                "error": "未提供认证token",
                "code": "TOKEN_MISSING"
            }), 401
        
        # 解析Bearer Token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                "success": False,
                "error": "无效的认证格式",
                "code": "TOKEN_INVALID_FORMAT"
            }), 401
        
        token = parts[1]
        
        # 解析Token
        payload = auth_service.decode_token(token)
        if not payload:
            return jsonify({
                "success": False,
                "error": "token已过期或无效",
                "code": "TOKEN_INVALID"
            }), 401
        
        # 将用户信息注入到请求上下文
        request.user_id = payload.get('user_id')
        request.user_role = payload.get('role')
        
        return f(*args, **kwargs)
    
    return decorated


def require_admin(f):
    """
    管理员权限装饰器
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # 先进行认证
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                "success": False,
                "error": "未提供认证token",
                "code": "TOKEN_MISSING"
            }), 401
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                "success": False,
                "error": "无效的认证格式",
                "code": "TOKEN_INVALID_FORMAT"
            }), 401
        
        token = parts[1]
        payload = auth_service.decode_token(token)
        
        if not payload:
            return jsonify({
                "success": False,
                "error": "token已过期或无效",
                "code": "TOKEN_INVALID"
            }), 401
        
        # 检查是否是管理员
        if payload.get('role') != 'admin':
            return jsonify({
                "success": False,
                "error": "权限不足，需要管理员权限",
                "code": "PERMISSION_DENIED"
            }), 403
        
        request.user_id = payload.get('user_id')
        request.user_role = payload.get('role')
        
        return f(*args, **kwargs)
    
    return decorated


# ==================== 认证接口 ====================

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录
    
    请求体:
    {
        "username": "admin",
        "password": "admin123"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
                "code": "INVALID_REQUEST"
            }), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({
                "success": False,
                "error": "用户名和密码不能为空",
                "code": "VALIDATION_ERROR"
            }), 400
        
        result = auth_service.login(username, password)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        logger.error(f"登录失败: {e}")
        return jsonify({
            "success": False,
            "error": "登录失败",
            "code": "LOGIN_ERROR"
        }), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    用户注册
    
    请求体:
    {
        "username": "newuser",
        "password": "password123"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
                "code": "INVALID_REQUEST"
            }), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({
                "success": False,
                "error": "用户名和密码不能为空",
                "code": "VALIDATION_ERROR"
            }), 400
        
        # 简单验证
        if len(username) < 3 or len(username) > 50:
            return jsonify({
                "success": False,
                "error": "用户名长度必须在3-50之间",
                "code": "VALIDATION_ERROR"
            }), 400
        
        if len(password) < 6:
            return jsonify({
                "success": False,
                "error": "密码长度不能少于6位",
                "code": "VALIDATION_ERROR"
            }), 400
        
        result = auth_service.register(username, password)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"注册失败: {e}")
        return jsonify({
            "success": False,
            "error": "注册失败",
            "code": "REGISTER_ERROR"
        }), 500


@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_me():
    """
    获取当前用户信息
    """
    try:
        result = auth_service.get_user_info(request.user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return jsonify({
            "success": False,
            "error": "获取用户信息失败",
            "code": "FETCH_ERROR"
        }), 500


@auth_bp.route('/password', methods=['PUT'])
@require_auth
def change_password():
    """
    修改当前用户密码
    
    请求体:
    {
        "old_password": "old123",
        "new_password": "new123"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
                "code": "INVALID_REQUEST"
            }), 400
        
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        
        if not old_password or not new_password:
            return jsonify({
                "success": False,
                "error": "旧密码和新密码不能为空",
                "code": "VALIDATION_ERROR"
            }), 400
        
        if len(new_password) < 6:
            return jsonify({
                "success": False,
                "error": "新密码长度不能少于6位",
                "code": "VALIDATION_ERROR"
            }), 400
        
        result = auth_service.change_password(request.user_id, old_password, new_password)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return jsonify({
            "success": False,
            "error": "修改密码失败",
            "code": "PASSWORD_CHANGE_ERROR"
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    用户登出
    (前端删除token即可，后端只需要返回成功)
    """
    return jsonify({
        "success": True,
        "message": "登出成功"
    }), 200
