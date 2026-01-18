"""
对话文件仓储
处理对话JSON文件的读写操作
"""
import json
import logging
import os
import fcntl
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from backend.models.entities import Message
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class ConversationFileRepository:
    """对话文件仓储"""
    
    # 聊天历史基础目录
    CHAT_HISTORY_DIR = os.path.join(settings.base_dir, "chat_history")
    
    def __init__(self):
        """初始化仓储，确保基础目录存在"""
        self._ensure_base_dir()
        logger.info(f"初始化 ConversationFileRepository: {self.CHAT_HISTORY_DIR}")
    
    def _ensure_base_dir(self):
        """确保基础目录存在"""
        try:
            os.makedirs(self.CHAT_HISTORY_DIR, exist_ok=True)
        except Exception as e:
            logger.error(f"创建基础目录失败: {e}")
            raise
    
    def _get_file_path(self, user_id: int, conversation_id: int) -> str:
        """
        生成文件路径
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            
        Returns:
            完整文件路径
        """
        user_dir = os.path.join(self.CHAT_HISTORY_DIR, f"user_{user_id}")
        file_name = f"conv_{conversation_id}.json"
        return os.path.join(user_dir, file_name)
    
    def _get_relative_path(self, user_id: int, conversation_id: int) -> str:
        """
        生成相对路径（用于存储到数据库）
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            
        Returns:
            相对路径
        """
        return f"chat_history/user_{user_id}/conv_{conversation_id}.json"
    
    def _ensure_user_dir(self, user_id: int):
        """
        确保用户目录存在
        
        Args:
            user_id: 用户ID
        """
        try:
            user_dir = os.path.join(self.CHAT_HISTORY_DIR, f"user_{user_id}")
            os.makedirs(user_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建用户目录失败: user_id={user_id}, error={e}")
            raise
    
    def create(
        self, 
        user_id: int, 
        conversation_id: int, 
        title: str
    ) -> str:
        """
        创建新的对话JSON文件
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            title: 对话标题
            
        Returns:
            相对文件路径
            
        Raises:
            Exception: 文件创建失败
        """
        try:
            self._ensure_user_dir(user_id)
            file_path = self._get_file_path(user_id, conversation_id)
            
            # 初始化对话数据
            data = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "title": title,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": []
            }
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            relative_path = self._get_relative_path(user_id, conversation_id)
            logger.info(f"创建对话文件成功: {relative_path}")
            return relative_path
        except Exception as e:
            logger.error(f"创建对话文件失败: user_id={user_id}, conversation_id={conversation_id}, error={e}")
            raise
    
    def read(self, user_id: int, conversation_id: int) -> List[Message]:
        """
        读取对话消息
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            
        Returns:
            Message实体列表
            
        Raises:
            FileNotFoundError: 文件不存在
            Exception: 读取或解析失败
        """
        try:
            file_path = self._get_file_path(user_id, conversation_id)
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"对话文件不存在: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            messages = []
            for msg_data in data.get('messages', []):
                messages.append(Message.from_dict(msg_data))
            
            logger.info(f"读取对话文件成功: conversation_id={conversation_id}, message_count={len(messages)}")
            return messages
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"读取对话文件失败: user_id={user_id}, conversation_id={conversation_id}, error={e}")
            raise
    
    def read_full_data(self, user_id: int, conversation_id: int) -> Dict[str, Any]:
        """
        读取完整对话数据（包含元数据）
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            
        Returns:
            完整对话数据字典
        """
        try:
            file_path = self._get_file_path(user_id, conversation_id)
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"对话文件不存在: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
        except Exception as e:
            logger.error(f"读取完整对话数据失败: user_id={user_id}, conversation_id={conversation_id}, error={e}")
            raise
    
    def append_message(
        self, 
        user_id: int, 
        conversation_id: int, 
        message: Message
    ) -> bool:
        """
        追加消息到对话文件（带文件锁）
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            message: Message实体
            
        Returns:
            是否成功
        """
        try:
            file_path = self._get_file_path(user_id, conversation_id)
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"对话文件不存在: {file_path}")
            
            # 使用文件锁防止并发写入
            with open(file_path, 'r+', encoding='utf-8') as f:
                # 获取排他锁
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                
                try:
                    # 读取现有数据
                    data = json.load(f)
                    
                    # 追加消息
                    data['messages'].append(message.to_dict())
                    
                    # 更新时间戳
                    data['updated_at'] = datetime.now().isoformat()
                    
                    # 写回文件
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"追加消息成功: conversation_id={conversation_id}, role={message.role}")
                    return True
                finally:
                    # 释放锁
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"追加消息失败: user_id={user_id}, conversation_id={conversation_id}, error={e}")
            raise
    
    def update_title(
        self, 
        user_id: int, 
        conversation_id: int, 
        title: str
    ) -> bool:
        """
        更新对话标题
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            title: 新标题
            
        Returns:
            是否成功
        """
        try:
            file_path = self._get_file_path(user_id, conversation_id)
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"对话文件不存在: {file_path}")
            
            with open(file_path, 'r+', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                
                try:
                    data = json.load(f)
                    data['title'] = title
                    data['updated_at'] = datetime.now().isoformat()
                    
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"更新标题成功: conversation_id={conversation_id}")
                    return True
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"更新标题失败: user_id={user_id}, conversation_id={conversation_id}, error={e}")
            raise
    
    def delete(self, user_id: int, conversation_id: int) -> bool:
        """
        删除对话文件
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            
        Returns:
            是否成功
        """
        try:
            file_path = self._get_file_path(user_id, conversation_id)
            
            if not os.path.exists(file_path):
                logger.warning(f"删除对话文件失败: 文件不存在 {file_path}")
                return False
            
            os.remove(file_path)
            logger.info(f"删除对话文件成功: conversation_id={conversation_id}")
            return True
        except Exception as e:
            logger.error(f"删除对话文件失败: user_id={user_id}, conversation_id={conversation_id}, error={e}")
            raise
    
    def exists(self, user_id: int, conversation_id: int) -> bool:
        """
        检查对话文件是否存在
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            
        Returns:
            是否存在
        """
        file_path = self._get_file_path(user_id, conversation_id)
        return os.path.exists(file_path)
    
    def get_file_size(self, user_id: int, conversation_id: int) -> int:
        """
        获取文件大小（字节）
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            
        Returns:
            文件大小（字节），如果文件不存在返回0
        """
        try:
            file_path = self._get_file_path(user_id, conversation_id)
            
            if not os.path.exists(file_path):
                return 0
            
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"获取文件大小失败: user_id={user_id}, conversation_id={conversation_id}, error={e}")
            return 0
