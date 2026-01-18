"""
对话数据库仓储
处理 conversations 表的 CRUD 操作
"""
import logging
from typing import List, Optional
from datetime import datetime

from backend.database.connection import execute_query, execute_update
from backend.models.entities import Conversation

logger = logging.getLogger(__name__)


class ConversationRepository:
    """对话数据库仓储"""
    
    def __init__(self):
        """初始化仓储"""
        logger.info("初始化 ConversationRepository")
    
    def create(self, user_id: int, title: str, file_path: str = "") -> int:
        """
        创建新对话
        
        Args:
            user_id: 用户ID
            title: 对话标题
            file_path: JSON文件路径（可选，稍后更新）
            
        Returns:
            新创建的对话ID
            
        Raises:
            Exception: 数据库操作失败
        """
        try:
            sql = """
                INSERT INTO conversations (user_id, title, file_path, message_count)
                VALUES (%s, %s, %s, 0)
            """
            conversation_id = execute_update(sql, (user_id, title, file_path))
            logger.info(f"创建对话成功: conversation_id={conversation_id}, user_id={user_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"创建对话失败: {e}")
            raise
    
    def get_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """
        根据ID获取对话
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Conversation实体，如果不存在返回None
        """
        try:
            sql = "SELECT * FROM conversations WHERE id = %s"
            results = execute_query(sql, (conversation_id,))
            
            if not results:
                return None
            
            row = results[0]
            return Conversation(
                id=row['id'],
                user_id=row['user_id'],
                title=row['title'],
                file_path=row['file_path'] or "",
                message_count=row['message_count'],
                created_at=row['created_at'].isoformat() if row['created_at'] else "",
                updated_at=row['updated_at'].isoformat() if row['updated_at'] else ""
            )
        except Exception as e:
            logger.error(f"查询对话失败: conversation_id={conversation_id}, error={e}")
            raise
    
    def get_by_user(
        self, 
        user_id: int, 
        offset: int = 0, 
        limit: int = 20
    ) -> List[Conversation]:
        """
        获取用户的所有对话（分页）
        
        Args:
            user_id: 用户ID
            offset: 偏移量
            limit: 每页数量
            
        Returns:
            Conversation实体列表
        """
        try:
            sql = """
                SELECT * FROM conversations 
                WHERE user_id = %s 
                ORDER BY updated_at DESC 
                LIMIT %s OFFSET %s
            """
            results = execute_query(sql, (user_id, limit, offset))
            
            conversations = []
            for row in results:
                conversations.append(Conversation(
                    id=row['id'],
                    user_id=row['user_id'],
                    title=row['title'],
                    file_path=row['file_path'] or "",
                    message_count=row['message_count'],
                    created_at=row['created_at'].isoformat() if row['created_at'] else "",
                    updated_at=row['updated_at'].isoformat() if row['updated_at'] else ""
                ))
            
            logger.info(f"查询用户对话成功: user_id={user_id}, count={len(conversations)}")
            return conversations
        except Exception as e:
            logger.error(f"查询用户对话失败: user_id={user_id}, error={e}")
            raise
    
    def update_title(self, conversation_id: int, title: str) -> bool:
        """
        更新对话标题
        
        Args:
            conversation_id: 对话ID
            title: 新标题
            
        Returns:
            是否成功
        """
        try:
            sql = "UPDATE conversations SET title = %s WHERE id = %s"
            affected_rows = execute_update(sql, (title, conversation_id))
            success = affected_rows > 0
            
            if success:
                logger.info(f"更新对话标题成功: conversation_id={conversation_id}")
            else:
                logger.warning(f"更新对话标题失败: conversation_id={conversation_id} 不存在")
            
            return success
        except Exception as e:
            logger.error(f"更新对话标题失败: conversation_id={conversation_id}, error={e}")
            raise
    
    def update_message_count(self, conversation_id: int, message_count: int) -> bool:
        """
        更新消息数量
        
        Args:
            conversation_id: 对话ID
            message_count: 新的消息数量
            
        Returns:
            是否成功
        """
        try:
            sql = "UPDATE conversations SET message_count = %s WHERE id = %s"
            affected_rows = execute_update(sql, (message_count, conversation_id))
            success = affected_rows > 0
            
            if success:
                logger.info(f"更新消息数量成功: conversation_id={conversation_id}, count={message_count}")
            
            return success
        except Exception as e:
            logger.error(f"更新消息数量失败: conversation_id={conversation_id}, error={e}")
            raise
    
    def update_file_path(self, conversation_id: int, file_path: str) -> bool:
        """
        更新文件路径
        
        Args:
            conversation_id: 对话ID
            file_path: JSON文件路径
            
        Returns:
            是否成功
        """
        try:
            sql = "UPDATE conversations SET file_path = %s WHERE id = %s"
            affected_rows = execute_update(sql, (file_path, conversation_id))
            success = affected_rows > 0
            
            if success:
                logger.info(f"更新文件路径成功: conversation_id={conversation_id}")
            
            return success
        except Exception as e:
            logger.error(f"更新文件路径失败: conversation_id={conversation_id}, error={e}")
            raise
    
    def delete(self, conversation_id: int, user_id: int) -> bool:
        """
        删除对话（需要验证用户权限）
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            是否成功
        """
        try:
            # 先检查对话是否属于该用户
            sql_check = "SELECT user_id FROM conversations WHERE id = %s"
            results = execute_query(sql_check, (conversation_id,))
            
            if not results:
                logger.warning(f"删除对话失败: conversation_id={conversation_id} 不存在")
                return False
            
            if results[0]['user_id'] != user_id:
                logger.warning(f"删除对话失败: 权限不足, conversation_id={conversation_id}, user_id={user_id}")
                return False
            
            # 执行删除
            sql_delete = "DELETE FROM conversations WHERE id = %s"
            affected_rows = execute_update(sql_delete, (conversation_id,))
            success = affected_rows > 0
            
            if success:
                logger.info(f"删除对话成功: conversation_id={conversation_id}")
            
            return success
        except Exception as e:
            logger.error(f"删除对话失败: conversation_id={conversation_id}, error={e}")
            raise
    
    def exists(self, conversation_id: int, user_id: Optional[int] = None) -> bool:
        """
        检查对话是否存在
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID（可选，用于权限验证）
            
        Returns:
            是否存在
        """
        try:
            if user_id is not None:
                sql = "SELECT COUNT(*) as count FROM conversations WHERE id = %s AND user_id = %s"
                results = execute_query(sql, (conversation_id, user_id))
            else:
                sql = "SELECT COUNT(*) as count FROM conversations WHERE id = %s"
                results = execute_query(sql, (conversation_id,))
            
            return results[0]['count'] > 0 if results else False
        except Exception as e:
            logger.error(f"检查对话存在性失败: conversation_id={conversation_id}, error={e}")
            raise
    
    def count_by_user(self, user_id: int) -> int:
        """
        统计用户的对话总数
        
        Args:
            user_id: 用户ID
            
        Returns:
            对话总数
        """
        try:
            sql = "SELECT COUNT(*) as count FROM conversations WHERE user_id = %s"
            results = execute_query(sql, (user_id,))
            return results[0]['count'] if results else 0
        except Exception as e:
            logger.error(f"统计用户对话数失败: user_id={user_id}, error={e}")
            raise
