"""
认证API路由
登录、注册、忘记密码、重置密码
"""
import logging
import secrets
from flask import Blueprint, request, jsonify
from backend.services.auth_service import auth_service
from backend.database.connection import execute_query, execute_update

logger = logging.getLogger(__name__)

# 创建蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


# ==================== 登录接口 ====================

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录
    
    请求体:
    {
        "username": "admin",
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
def get_me():
    """
    获取当前用户信息
    
    请求头:
    Authorization: Bearer <token>
    """
    try:
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
        
        user_id = payload.get('user_id')
        result = auth_service.get_user_info(user_id)
        
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
def change_password():
    """
    修改当前用户密码（需要旧密码）
    
    请求体:
    {
        "old_password": "oldpassword",
        "new_password": "newpassword"
    }
    """
    try:
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
        
        user_id = payload.get('user_id')
        
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
                "error": "旧密码和新密码都不能为空",
                "code": "VALIDATION_ERROR"
            }), 400
        
        result = auth_service.change_password(user_id, old_password, new_password)
        
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


# ==================== 忘记密码接口 ====================

@auth_bp.route('/forgot-password/initiate', methods=['POST'])
def initiate_password_reset():
    """
    发起密码重置 - 步骤1：输入用户名，检查安全问题
    
    请求体:
    {
        "username": "用户名"
    }
    
    响应:
    {
        "success": true,
        "data": {
            "has_security_questions": true/false,
            "questions": ["问题1", "问题2", "问题3"]  // 如果有设置安全问题
        }
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
        
        if not username:
            return jsonify({
                "success": False,
                "error": "用户名不能为空",
                "code": "VALIDATION_ERROR"
            }), 400
        
        # 检查用户是否存在
        user = auth_service.get_user_by_username(username)
        if not user:
            return jsonify({
                "success": False,
                "error": "用户不存在",
                "code": "USER_NOT_FOUND"
            }), 404
        
        # 获取安全问题
        sql = "SELECT security_questions FROM users WHERE id = %s"
        results = execute_query(sql, (user['id'],))
        
        security_questions = []
        has_questions = False
        
        if results and results[0]['security_questions']:
            import json
            try:
                questions_data = json.loads(results[0]['security_questions'])
                if isinstance(questions_data, list) and len(questions_data) > 0:
                    security_questions = [q['question'] for q in questions_data]
                    has_questions = True
            except:
                pass
        
        return jsonify({
            "success": True,
            "data": {
                "has_security_questions": has_questions,
                "questions": security_questions
            }
        }), 200
        
    except Exception as e:
        logger.error(f"发起密码重置失败: {e}")
        return jsonify({
            "success": False,
            "error": "操作失败",
            "code": "RESET_ERROR"
        }), 500


@auth_bp.route('/forgot-password/verify', methods=['POST'])
def verify_security_answers():
    """
    验证安全问题答案 - 步骤2：验证答案，设置新密码
    
    请求体:
    {
        "username": "用户名",
        "answers": ["答案1", "答案2", "答案3"],
        "new_password": "新密码"
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
        answers = data.get('answers', [])
        new_password = data.get('new_password', '')
        
        if not username:
            return jsonify({
                "success": False,
                "error": "用户名不能为空",
                "code": "VALIDATION_ERROR"
            }), 400
        
        if not answers or not isinstance(answers, list):
            return jsonify({
                "success": False,
                "error": "请提供安全问题答案",
                "code": "VALIDATION_ERROR"
            }), 400
        
        if not new_password or len(new_password) < 6:
            return jsonify({
                "success": False,
                "error": "新密码长度不能少于6位",
                "code": "VALIDATION_ERROR"
            }), 400
        
        # 检查用户是否存在
        user = auth_service.get_user_by_username(username)
        if not user:
            return jsonify({
                "success": False,
                "error": "用户不存在",
                "code": "USER_NOT_FOUND"
            }), 404
        
        # 获取安全问题
        sql = "SELECT security_questions FROM users WHERE id = %s"
        results = execute_query(sql, (user['id'],))
        
        if not results or not results[0]['security_questions']:
            return jsonify({
                "success": False,
                "error": "该用户未设置安全问题，请联系管理员重置密码",
                "code": "NO_SECURITY_QUESTIONS"
            }), 400
        
        import json
        try:
            questions_data = json.loads(results[0]['security_questions'])
        except:
            return jsonify({
                "success": False,
                "error": "安全问题数据格式错误",
                "code": "INVALID_FORMAT"
            }), 400
        
        # 验证答案（不区分大小写）
        all_correct = True
        for i, qa in enumerate(questions_data):
            if i >= len(answers):
                all_correct = False
                break
            stored_answer = qa.get('answer', '').strip().lower()
            provided_answer = str(answers[i]).strip().lower()
            if stored_answer != provided_answer:
                all_correct = False
                break
        
        if not all_correct:
            return jsonify({
                "success": False,
                "error": "安全问题答案不正确",
                "code": "WRONG_ANSWERS"
            }), 400
        
        # 验证通过，更新密码
        encrypted_password = auth_service.encrypt_password(new_password)
        sql = "UPDATE users SET password = %s WHERE id = %s"
        execute_update(sql, (encrypted_password, user['id']))
        
        return jsonify({
            "success": True,
            "message": "密码重置成功，请使用新密码登录"
        }), 200
        
    except Exception as e:
        logger.error(f"验证安全问题失败: {e}")
        return jsonify({
            "success": False,
            "error": "操作失败",
            "code": "VERIFY_ERROR"
        }), 500


@auth_bp.route('/security-questions', methods=['PUT'])
def update_security_questions():
    """
    设置/更新安全问题
    
    请求体:
    {
        "questions": [
            {"question": "问题1", "answer": "答案1"},
            {"question": "问题2", "answer": "答案2"},
            {"question": "问题3", "answer": "答案3"}
        ]
    }
    """
    try:
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
        
        user_id = payload.get('user_id')
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
                "code": "INVALID_REQUEST"
            }), 400
        
        questions = data.get('questions', [])
        
        if not questions or not isinstance(questions, list):
            return jsonify({
                "success": False,
                "error": "请提供安全问题设置",
                "code": "VALIDATION_ERROR"
            }), 400
        
        if len(questions) < 1 or len(questions) > 3:
            return jsonify({
                "success": False,
                "error": "安全问题数量必须在1-3个之间",
                "code": "VALIDATION_ERROR"
            }), 400
        
        # 验证问题格式
        for i, qa in enumerate(questions):
            if not qa.get('question') or not qa.get('answer'):
                return jsonify({
                    "success": False,
                    "error": f"第{i+1}个问题缺少问题或答案",
                    "code": "VALIDATION_ERROR"
                }), 400
        
        # 保存安全问题
        import json
        sql = "UPDATE users SET security_questions = %s WHERE id = %s"
        execute_update(sql, (json.dumps(questions), user_id))
        
        return jsonify({
            "success": True,
            "message": "安全问题设置成功"
        }), 200
        
    except Exception as e:
        logger.error(f"设置安全问题失败: {e}")
        return jsonify({
            "success": False,
            "error": "设置失败",
            "code": "SET_ERROR"
        }), 500


@auth_bp.route('/security-questions', methods=['GET'])
def get_security_questions():
    """
    获取当前用户设置的安全问题（只返回问题，不返回答案）
    """
    try:
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
        
        user_id = payload.get('user_id')
        
        sql = "SELECT security_questions FROM users WHERE id = %s"
        results = execute_query(sql, (user_id,))
        
        if not results:
            return jsonify({
                "success": False,
                "error": "用户不存在",
                "code": "USER_NOT_FOUND"
            }), 404
        
        questions = []
        if results[0]['security_questions']:
            import json
            try:
                questions_data = json.loads(results[0]['security_questions'])
                questions = [qa['question'] for qa in questions_data]
            except:
                pass
        
        return jsonify({
            "success": True,
            "data": {
                "questions": questions,
                "has_questions": len(questions) > 0
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取安全问题失败: {e}")
        return jsonify({
            "success": False,
            "error": "获取失败",
            "code": "FETCH_ERROR"
        }), 500
