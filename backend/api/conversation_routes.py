"""
对话管理 API 路由
提供对话的 CRUD 接口
"""
import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any

from backend.services.conversation_service import ConversationService
from backend.models.dtos import ErrorResponse

logger = logging.getLogger(__name__)

# 创建蓝图
conversation_bp = Blueprint('conversations', __name__, url_prefix='/api/conversations')

# 全局服务实例（懒加载）
_conversation_service = None


def get_conversation_service() -> ConversationService:
    """获取对话服务实例（懒加载）"""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service


# ============== API 端点 ==============

@conversation_bp.route('', methods=['POST'])
def create_conversation():
    """
    创建新对话
    
    请求体:
    {
        "user_id": 1,
        "title": "对话标题" (可选)
    }
    
    响应: 201
    {
        "conversation_id": 1,
        "user_id": 1,
        "title": "对话标题",
        "file_path": "chat_history/user_1/conv_1.json",
        "message_count": 0,
        "created_at": "2024-01-18T10:00:00",
        "updated_at": "2024-01-18T10:00:00"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="请求体不能为空",
                code="INVALID_REQUEST"
            ).to_dict()), 400
        
        user_id = data.get('user_id')
        title = data.get('title')
        
        if not user_id:
            return jsonify(ErrorResponse(
                error="user_id 不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        service = get_conversation_service()
        result = service.create_conversation(user_id, title)
        
        logger.info(f"创建对话成功: conversation_id={result['conversation_id']}, user_id={user_id}")
        return jsonify(result), 201
        
    except ValueError as e:
        logger.error(f"创建对话参数错误: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="VALIDATION_ERROR"
        ).to_dict()), 400
    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="CREATE_ERROR"
        ).to_dict()), 500


@conversation_bp.route('', methods=['GET'])
def get_conversation_list():
    """
    获取用户的对话列表
    
    查询参数:
    - user_id: 用户ID (必需)
    - page: 页码，默认1
    - page_size: 每页数量，默认20
    
    响应: 200
    {
        "conversations": [...],
        "total_count": 10,
        "page": 1,
        "page_size": 20
    }
    """
    try:
        user_id = request.args.get('user_id', type=int)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        if not user_id:
            return jsonify(ErrorResponse(
                error="user_id 不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        service = get_conversation_service()
        response = service.get_conversation_list(user_id, page, page_size)
        
        logger.info(f"获取对话列表成功: user_id={user_id}, count={response.total_count}")
        return jsonify(response.to_dict()), 200
        
    except ValueError as e:
        logger.error(f"获取对话列表参数错误: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="VALIDATION_ERROR"
        ).to_dict()), 400
    except Exception as e:
        logger.error(f"获取对话列表失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="QUERY_ERROR"
        ).to_dict()), 500


@conversation_bp.route('/<int:conversation_id>', methods=['GET'])
def get_conversation_detail(conversation_id: int):
    """
    获取对话详情（包含完整消息）
    
    路径参数:
    - conversation_id: 对话ID
    
    查询参数:
    - user_id: 用户ID (必需)
    
    响应: 200
    {
        "conversation_id": 1,
        "user_id": 1,
        "title": "对话标题",
        "messages": [...],
        "message_count": 5,
        "created_at": "2024-01-18T10:00:00",
        "updated_at": "2024-01-18T10:05:00"
    }
    """
    try:
        user_id = request.args.get('user_id', type=int)
        
        if not user_id:
            return jsonify(ErrorResponse(
                error="user_id 不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        service = get_conversation_service()
        response = service.get_conversation_detail(conversation_id, user_id)
        
        logger.info(f"获取对话详情成功: conversation_id={conversation_id}")
        return jsonify(response.to_dict()), 200
        
    except ValueError as e:
        logger.error(f"获取对话详情参数错误: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="VALIDATION_ERROR"
        ).to_dict()), 400
    except FileNotFoundError as e:
        logger.error(f"对话不存在: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="NOT_FOUND"
        ).to_dict()), 404
    except PermissionError as e:
        logger.error(f"权限不足: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="PERMISSION_DENIED"
        ).to_dict()), 403
    except Exception as e:
        logger.error(f"获取对话详情失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="QUERY_ERROR"
        ).to_dict()), 500


@conversation_bp.route('/<int:conversation_id>/messages', methods=['POST'])
def add_message(conversation_id: int):
    """
    添加消息到对话
    
    路径参数:
    - conversation_id: 对话ID
    
    请求体:
    {
        "user_id": 1,
        "message": {
            "role": "user",
            "content": "消息内容",
            "queryMode": "文献检索" (可选),
            "expert": "literature" (可选),
            "steps": [...] (可选),
            "references": [...] (可选)
        }
    }
    
    响应: 201
    {
        "success": true,
        "message": "消息添加成功"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="请求体不能为空",
                code="INVALID_REQUEST"
            ).to_dict()), 400
        
        user_id = data.get('user_id')
        message_data = data.get('message')
        
        if not user_id:
            return jsonify(ErrorResponse(
                error="user_id 不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        if not message_data:
            return jsonify(ErrorResponse(
                error="message 不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        service = get_conversation_service()
        service.add_message(conversation_id, user_id, message_data)
        
        logger.info(f"添加消息成功: conversation_id={conversation_id}, role={message_data.get('role')}")
        return jsonify({
            "success": True,
            "message": "消息添加成功"
        }), 201
        
    except ValueError as e:
        logger.error(f"添加消息参数错误: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="VALIDATION_ERROR"
        ).to_dict()), 400
    except FileNotFoundError as e:
        logger.error(f"对话不存在: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="NOT_FOUND"
        ).to_dict()), 404
    except PermissionError as e:
        logger.error(f"权限不足: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="PERMISSION_DENIED"
        ).to_dict()), 403
    except Exception as e:
        logger.error(f"添加消息失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="ADD_MESSAGE_ERROR"
        ).to_dict()), 500


@conversation_bp.route('/<int:conversation_id>', methods=['PUT'])
def update_conversation(conversation_id: int):
    """
    更新对话标题
    
    路径参数:
    - conversation_id: 对话ID
    
    请求体:
    {
        "user_id": 1,
        "title": "新标题"
    }
    
    响应: 200
    {
        "success": true,
        "message": "标题更新成功"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="请求体不能为空",
                code="INVALID_REQUEST"
            ).to_dict()), 400
        
        user_id = data.get('user_id')
        title = data.get('title')
        
        if not user_id:
            return jsonify(ErrorResponse(
                error="user_id 不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        if not title:
            return jsonify(ErrorResponse(
                error="title 不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        service = get_conversation_service()
        service.update_conversation_title(conversation_id, user_id, title)
        
        logger.info(f"更新标题成功: conversation_id={conversation_id}")
        return jsonify({
            "success": True,
            "message": "标题更新成功"
        }), 200
        
    except ValueError as e:
        logger.error(f"更新标题参数错误: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="VALIDATION_ERROR"
        ).to_dict()), 400
    except FileNotFoundError as e:
        logger.error(f"对话不存在: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="NOT_FOUND"
        ).to_dict()), 404
    except PermissionError as e:
        logger.error(f"权限不足: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="PERMISSION_DENIED"
        ).to_dict()), 403
    except Exception as e:
        logger.error(f"更新标题失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="UPDATE_ERROR"
        ).to_dict()), 500


@conversation_bp.route('/<int:conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id: int):
    """
    删除对话
    
    路径参数:
    - conversation_id: 对话ID
    
    查询参数:
    - user_id: 用户ID (必需)
    
    响应: 204 (无内容)
    """
    try:
        user_id = request.args.get('user_id', type=int)
        
        if not user_id:
            return jsonify(ErrorResponse(
                error="user_id 不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        service = get_conversation_service()
        service.delete_conversation(conversation_id, user_id)
        
        logger.info(f"删除对话成功: conversation_id={conversation_id}")
        return '', 204
        
    except ValueError as e:
        logger.error(f"删除对话参数错误: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="VALIDATION_ERROR"
        ).to_dict()), 400
    except FileNotFoundError as e:
        logger.error(f"对话不存在: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="NOT_FOUND"
        ).to_dict()), 404
    except PermissionError as e:
        logger.error(f"权限不足: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="PERMISSION_DENIED"
        ).to_dict()), 403
    except Exception as e:
        logger.error(f"删除对话失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="DELETE_ERROR"
        ).to_dict()), 500


# ============== 错误处理 ==============

@conversation_bp.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify(ErrorResponse(
        error="请求的资源不存在",
        code="NOT_FOUND"
    ).to_dict()), 404


@conversation_bp.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify(ErrorResponse(
        error="服务器内部错误",
        code="INTERNAL_ERROR"
    ).to_dict()), 500
