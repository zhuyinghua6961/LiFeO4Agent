"""
管理员API路由
用户管理、权限控制
"""
import logging
from flask import Blueprint, request, jsonify
from backend.services.auth_service import auth_service
from backend.database.connection import execute_query, execute_update

logger = logging.getLogger(__name__)

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def require_admin(f):
    """
    管理员权限装饰器
    """
    from functools import wraps
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


# ==================== 管理员接口 ====================

@admin_bp.route('/users', methods=['GET'])
@require_admin
def get_users():
    """
    获取所有用户列表（管理员）
    
    Query参数:
    - page: 页码，默认1
    - page_size: 每页数量，默认10
    
    响应:
    {
        "success": true,
        "data": [
            {"id": 1, "username": "admin", "role": "admin", "status": "active", "created_at": "..."}
        ]
    }
    """
    try:
        # 分页参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        
        # 获取总数
        count_sql = "SELECT COUNT(*) as total FROM users"
        count_result = execute_query(count_sql)
        total = count_result[0]['total'] if count_result else 0
        
        # 获取用户列表
        offset = (page - 1) * page_size
        sql = """
            SELECT id, username, role, status, created_at
            FROM users
            ORDER BY id ASC
            LIMIT %s OFFSET %s
        """
        users = execute_query(sql, (page_size, offset))
        
        # 格式化结果
        data = []
        for user in users:
            data.append({
                "id": user['id'],
                "username": user['username'],
                "role": user['role'],
                "status": user['status'],
                "created_at": user['created_at'].isoformat() if user['created_at'] else None
            })
        
        return jsonify({
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return jsonify({
            "success": False,
            "error": "获取用户列表失败",
            "code": "FETCH_ERROR"
        }), 500


@admin_bp.route('/users/<int:user_id>/password', methods=['PUT'])
@require_admin
def change_user_password(user_id: int):
    """
    修改任意用户密码（管理员）
    
    请求体:
    {
        "new_password": "newpassword123"
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
        
        new_password = data.get('new_password', '')
        
        if not new_password:
            return jsonify({
                "success": False,
                "error": "新密码不能为空",
                "code": "VALIDATION_ERROR"
            }), 400
        
        if len(new_password) < 6:
            return jsonify({
                "success": False,
                "error": "密码长度不能少于6位",
                "code": "VALIDATION_ERROR"
            }), 400
        
        # 检查用户是否存在
        user = auth_service.get_user_by_id(user_id)
        if not user:
            return jsonify({
                "success": False,
                "error": "用户不存在",
                "code": "USER_NOT_FOUND"
            }), 404
        
        # 不能修改自己的密码（管理员应该使用普通修改密码接口）
        if user_id == request.user_id:
            return jsonify({
                "success": False,
                "error": "请使用 /api/auth/password 接口修改自己的密码",
                "code": "PERMISSION_DENIED"
            }), 400
        
        # 加密新密码
        hashed_password = auth_service.hash_password(new_password)
        
        # 更新密码
        sql = "UPDATE users SET password = %s WHERE id = %s"
        execute_update(sql, (hashed_password, user_id))
        
        return jsonify({
            "success": True,
            "message": f"用户 {user['username']} 的密码已修改"
        }), 200
        
    except Exception as e:
        logger.error(f"修改用户密码失败: {e}")
        return jsonify({
            "success": False,
            "error": "修改密码失败",
            "code": "PASSWORD_CHANGE_ERROR"
        }), 500


@admin_bp.route('/users/<int:user_id>/status', methods=['PUT'])
@require_admin
def change_user_status(user_id: int):
    """
    停用/启用用户（管理员）
    
    请求体:
    {
        "status": "disabled"  // 或 "active"
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
        
        status = data.get('status', '')
        
        if status not in ('active', 'disabled'):
            return jsonify({
                "success": False,
                "error": "状态必须是 active 或 disabled",
                "code": "VALIDATION_ERROR"
            }), 400
        
        # 检查用户是否存在
        user = auth_service.get_user_by_id(user_id)
        if not user:
            return jsonify({
                "success": False,
                "error": "用户不存在",
                "code": "USER_NOT_FOUND"
            }), 404
        
        # 不能停用自己
        if user_id == request.user_id:
            return jsonify({
                "success": False,
                "error": "不能停用自己的账号",
                "code": "PERMISSION_DENIED"
            }), 400
        
        # 不能修改管理员的状态（可选限制）
        if user['role'] == 'admin' and status == 'disabled':
            return jsonify({
                "success": False,
                "error": "不能停用管理员账号",
                "code": "PERMISSION_DENIED"
            }), 400
        
        # 更新状态
        sql = "UPDATE users SET status = %s WHERE id = %s"
        execute_update(sql, (status, user_id))
        
        message = "用户已停用" if status == 'disabled' else "用户已启用"
        
        return jsonify({
            "success": True,
            "message": message
        }), 200
        
    except Exception as e:
        logger.error(f"修改用户状态失败: {e}")
        return jsonify({
            "success": False,
            "error": "修改用户状态失败",
            "code": "STATUS_CHANGE_ERROR"
        }), 500


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id: int):
    """
    删除用户（管理员）
    """
    try:
        # 检查用户是否存在
        user = auth_service.get_user_by_id(user_id)
        if not user:
            return jsonify({
                "success": False,
                "error": "用户不存在",
                "code": "USER_NOT_FOUND"
            }), 404
        
        # 不能删除自己
        if user_id == request.user_id:
            return jsonify({
                "success": False,
                "error": "不能删除自己的账号",
                "code": "PERMISSION_DENIED"
            }), 400
        
        # 不能删除管理员（可选限制）
        if user['role'] == 'admin':
            return jsonify({
                "success": False,
                "error": "不能删除管理员账号",
                "code": "PERMISSION_DENIED"
            }), 400
        
        # 删除用户（会级联删除对话）
        sql = "DELETE FROM users WHERE id = %s"
        execute_update(sql, (user_id,))
        
        return jsonify({
            "success": True,
            "message": f"用户 {user['username']} 已删除"
        }), 200
        
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        return jsonify({
            "success": False,
            "error": "删除用户失败",
            "code": "DELETE_ERROR"
        }), 500
