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
            SELECT id, username, role, status, user_type, created_at
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
                "user_type": user.get('user_type', 3),  # 默认为3（普通用户）
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
        encrypted_password = auth_service.encrypt_password(new_password)
        
        # 更新密码
        sql = "UPDATE users SET password = %s WHERE id = %s"
        execute_update(sql, (encrypted_password, user_id))
        
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


@admin_bp.route('/users/<int:user_id>/password', methods=['GET'])
@require_admin
def get_user_password(user_id: int):
    """
    获取用户密码（管理员）- AES解密后可查看明文
    
    响应:
    {
        "success": true,
        "data": {
            "password": "明文密码"
        }
    }
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
        
        # 获取加密的密码
        sql = "SELECT password FROM users WHERE id = %s"
        results = execute_query(sql, (user_id,))
        if not results:
            return jsonify({
                "success": False,
                "error": "用户密码不存在",
                "code": "PASSWORD_NOT_FOUND"
            }), 404
        
        encrypted_password = results[0]['password']
        decrypted_password = auth_service.decrypt_password(encrypted_password)
        
        return jsonify({
            "success": True,
            "data": {
                "username": user['username'],
                "password": decrypted_password
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取用户密码失败: {e}")
        return jsonify({
            "success": False,
            "error": "获取密码失败",
            "code": "PASSWORD_FETCH_ERROR"
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


@admin_bp.route('/users', methods=['POST'])
@require_admin
def create_user():
    """
    创建新用户（管理员）
    
    请求体:
    {
        "username": "newuser",
        "password": "password123",
        "user_type": "super"  // 可选：super 或 common，默认 common
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
        user_type_str = data.get('user_type', 'common').strip().lower()
        
        if not username or not password:
            return jsonify({
                "success": False,
                "error": "用户名和密码不能为空",
                "code": "VALIDATION_ERROR"
            }), 400
        
        # 用户名长度验证
        if len(username) < 3 or len(username) > 50:
            return jsonify({
                "success": False,
                "error": "用户名长度必须在3-50之间",
                "code": "VALIDATION_ERROR"
            }), 400
        
        # 密码长度验证
        if len(password) < 6:
            return jsonify({
                "success": False,
                "error": "密码长度不能少于6位",
                "code": "VALIDATION_ERROR"
            }), 400
        
        # 验证用户类型
        if user_type_str not in ('super', 'common'):
            return jsonify({
                "success": False,
                "error": "用户类型必须是 super 或 common",
                "code": "VALIDATION_ERROR"
            }), 400
        
        # 映射用户类型为数字编码
        user_type_code = 2 if user_type_str == 'super' else 3
        
        # 检查用户名是否以 admin 开头（管理员账号保留）
        if username.lower().startswith('admin'):
            return jsonify({
                "success": False,
                "error": "不能创建以 admin 为前缀的用户名",
                "code": "USERNAME_INVALID"
            }), 400
        
        # 检查用户名是否已存在
        existing = auth_service.get_user_by_username(username)
        if existing:
            return jsonify({
                "success": False,
                "error": "用户名已存在",
                "code": "USERNAME_EXISTS"
            }), 400
        
        # 加密密码
        encrypted_password = auth_service.encrypt_password(password)
        
        # 根据用户类型设置 role
        role = 'super' if user_type_str == 'super' else 'user'
        
        sql = """
            INSERT INTO users (username, password, role, status, user_type, created_at)
            VALUES (%s, %s, %s, 'active', %s, NOW())
        """
        user_id = execute_update(sql, (username, encrypted_password, role, user_type_code))
        
        return jsonify({
            "success": True,
            "message": f"用户 {username} 创建成功",
            "data": {
                "id": user_id,
                "username": username,
                "role": role,
                "user_type": user_type_code,
                "status": "active"
            }
        }), 201
        
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        return jsonify({
            "success": False,
            "error": "创建用户失败",
            "code": "CREATE_ERROR"
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


# ==================== 批量导入接口 ====================

@admin_bp.route('/users/batch-import', methods=['POST'])
@require_admin
def batch_import_users():
    """
    批量导入用户（管理员）
    
    请求:
    - Content-Type: multipart/form-data
    - file: 上传的文件（.xlsx或.csv）
    
    响应:
    {
        "success": true,
        "message": "批量导入完成",
        "data": {
            "summary": {"total": 100, "success": 95, "failed": 3, "skipped": 2},
            "details": [...]
        }
    }
    """
    import os
    import uuid
    from werkzeug.utils import secure_filename
    from backend.services.file_parser import FileParser
    from backend.services.batch_import_service import BatchImportService
    
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "未提供文件",
                "code": "FILE_MISSING"
            }), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "文件名为空",
                "code": "FILENAME_EMPTY"
            }), 400
        
        # 检查文件类型
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext not in ('xlsx', 'csv'):
            return jsonify({
                "success": False,
                "error": "不支持的文件格式，只支持.xlsx和.csv",
                "code": "INVALID_FILE_TYPE"
            }), 400
        
        # 检查文件大小（5MB）
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        max_size = 5 * 1024 * 1024  # 5MB
        if file_size > max_size:
            return jsonify({
                "success": False,
                "error": "文件大小超过5MB限制",
                "code": "FILE_TOO_LARGE"
            }), 400
        
        # 保存到临时目录
        temp_dir = '/tmp/batch_import'
        os.makedirs(temp_dir, exist_ok=True)
        
        # 使用UUID生成唯一文件名
        temp_filename = f"{uuid.uuid4()}.{file_ext}"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        file.save(temp_path)
        
        try:
            # 解析文件
            parser = FileParser()
            df = parser.parse_file(temp_path, file_ext)
            
            # 批量导入
            import_service = BatchImportService()
            result = import_service.import_users(df)
            
            # 记录操作日志
            logger.info(f"管理员 {request.user_id} 批量导入用户: 总数={result.total}, 成功={result.success}, 失败={result.failed}, 跳过={result.skipped}")
            
            return jsonify({
                "success": True,
                "message": "批量导入完成",
                "data": {
                    "summary": {
                        "total": result.total,
                        "success": result.success,
                        "failed": result.failed,
                        "skipped": result.skipped
                    },
                    "details": result.details,
                    "duration": round(result.duration, 2)
                }
            }), 200
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except ValueError as e:
        logger.error(f"批量导入数据验证失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "code": "VALIDATION_ERROR"
        }), 400
    
    except Exception as e:
        logger.error(f"批量导入失败: {e}")
        return jsonify({
            "success": False,
            "error": "批量导入失败",
            "code": "IMPORT_ERROR"
        }), 500


@admin_bp.route('/users/import-template', methods=['GET'])
@require_admin
def download_import_template():
    """
    下载导入模板（管理员）
    
    Query参数:
    - format: 模板格式（xlsx或csv），默认xlsx
    
    响应:
    - Excel或CSV文件
    """
    import io
    import pandas as pd
    from flask import send_file
    
    try:
        # 获取格式参数
        file_format = request.args.get('format', 'xlsx').lower()
        
        if file_format not in ('xlsx', 'csv'):
            return jsonify({
                "success": False,
                "error": "不支持的格式，只支持xlsx和csv",
                "code": "INVALID_FORMAT"
            }), 400
        
        # 创建模板数据
        template_data = {
            'username': ['user001', 'user002', 'user003'],
            'password': ['Pass123!', 'Test456@', 'Demo789#'],
            'user_type': ['common', 'super', 'common']
        }
        
        df = pd.DataFrame(template_data)
        
        # 生成文件
        if file_format == 'xlsx':
            # 生成Excel文件
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='用户导入')
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='user_import_template.xlsx'
            )
        else:
            # 生成CSV文件
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')  # 使用utf-8-sig以支持Excel打开
            output.seek(0)
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8-sig')),
                mimetype='text/csv',
                as_attachment=True,
                download_name='user_import_template.csv'
            )
    
    except Exception as e:
        logger.error(f"下载模板失败: {e}")
        return jsonify({
            "success": False,
            "error": "下载模板失败",
            "code": "TEMPLATE_ERROR"
        }), 500
