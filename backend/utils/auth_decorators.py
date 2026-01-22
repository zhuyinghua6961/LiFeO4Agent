"""
认证装饰器
用于保护需要认证的API端点
"""
import logging
from functools import wraps
from flask import request, jsonify
from backend.services.auth_service import auth_service

logger = logging.getLogger(__name__)


def require_auth(f):
    """
    认证装饰器 - 要求请求必须携带有效的 JWT token
    
    使用方法:
    @require_auth
    def my_endpoint():
        # 可以通过 request.user_id 和 request.user_role 访问用户信息
        pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取 Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                "success": False,
                "error": "未提供认证token",
                "code": "TOKEN_MISSING"
            }), 401
        
        # 解析 Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                "success": False,
                "error": "无效的认证格式",
                "code": "TOKEN_INVALID_FORMAT"
            }), 401
        
        token = parts[1]
        
        # 验证 token
        payload = auth_service.decode_token(token)
        if not payload:
            return jsonify({
                "success": False,
                "error": "token已过期或无效",
                "code": "TOKEN_INVALID"
            }), 401
        
        # 检查用户状态（实时查询数据库）
        user_id = payload.get('user_id')
        user = auth_service.get_user_by_id(user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "error": "用户不存在",
                "code": "USER_NOT_FOUND"
            }), 401
        
        if user['status'] == 'disabled':
            return jsonify({
                "success": False,
                "error": "您的账号已被停用，请联系管理员",
                "code": "ACCOUNT_DISABLED"
            }), 403
        
        # 将用户信息附加到 request 对象
        request.user_id = payload.get('user_id')
        request.user_role = payload.get('role')
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_admin(f):
    """
    管理员权限装饰器 - 要求用户必须是管理员
    
    注意：必须与 @require_auth 一起使用
    
    使用方法:
    @require_auth
    @require_admin
    def admin_endpoint():
        pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查用户角色
        if not hasattr(request, 'user_role') or request.user_role != 'admin':
            return jsonify({
                "success": False,
                "error": "需要管理员权限",
                "code": "ADMIN_REQUIRED"
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """
    可选认证装饰器 - token 可选，如果提供则验证
    
    使用方法:
    @optional_auth
    def my_endpoint():
        # 如果有 token，可以通过 request.user_id 访问
        # 如果没有 token，request.user_id 为 None
        pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取 Authorization header
        auth_header = request.headers.get('Authorization')
        
        # 如果没有提供 token，设置为 None 并继续
        if not auth_header:
            request.user_id = None
            request.user_role = None
            return f(*args, **kwargs)
        
        # 解析 Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            request.user_id = None
            request.user_role = None
            return f(*args, **kwargs)
        
        token = parts[1]
        
        # 验证 token
        payload = auth_service.decode_token(token)
        if payload:
            user_id = payload.get('user_id')
            
            # 检查用户状态（实时查询数据库）
            user = auth_service.get_user_by_id(user_id)
            
            if user and user['status'] == 'active':
                # 只有用户存在且状态为 active 时才设置用户信息
                request.user_id = user_id
                request.user_role = payload.get('role')
            else:
                # 用户不存在或已停用，返回错误
                if user and user['status'] == 'disabled':
                    return jsonify({
                        "success": False,
                        "error": "您的账号已被停用，请联系管理员",
                        "code": "ACCOUNT_DISABLED"
                    }), 403
                else:
                    request.user_id = None
                    request.user_role = None
        else:
            request.user_id = None
            request.user_role = None
        
        return f(*args, **kwargs)
    
    return decorated_function
