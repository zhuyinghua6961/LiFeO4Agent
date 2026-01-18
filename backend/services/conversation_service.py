"""
对话服务层
协调数据库和文件操作，处理业务逻辑
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.conversation_file_repository import ConversationFileRepository
from backend.models.entities import Conversation, Message
from backend.models.dtos import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationDetailResponse,
    MessageAddRequest,
    ConversationUpdateRequest
)

logger = logging.getLogger(__name__)


class ConversationService:
    """对话服务"""
    
    def __init__(
        self,
        db_repo: Optional[ConversationRepository] = None,
        file_repo: Optional[ConversationFileRepository] = None
    ):
        """
        初始化服务
        
        Args:
            db_repo: 数据库仓储（可选，用于依赖注入）
            file_repo: 文件仓储（可选，用于依赖注入）
        """
        self.db_repo = db_repo or ConversationRepository()
        self.file_repo = file_repo or ConversationFileRepository()
        logger.info("初始化 ConversationService")
    
    def create_conversation(
        self, 
        user_id: int, 
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建新对话
        
        Args:
            user_id: 用户ID
            title: 对话标题（可选，默认为"新对话"）
            
        Returns:
            包含conversation_id和详情的字典
            
        Raises:
            Exception: 创建失败
        """
        try:
            # 验证请求
            request = ConversationCreateRequest(user_id=user_id, title=title)
            errors = request.validate()
            if errors:
                raise ValueError(f"参数验证失败: {', '.join(errors)}")
            
            # 使用默认标题
            if not title:
                title = "新对话"
            
            # 1. 在数据库创建记录（file_path暂时为空）
            conversation_id = self.db_repo.create(user_id, title, "")
            logger.info(f"数据库创建对话成功: conversation_id={conversation_id}")
            
            # 2. 创建JSON文件
            try:
                file_path = self.file_repo.create(user_id, conversation_id, title)
                logger.info(f"文件创建成功: {file_path}")
                
                # 3. 更新数据库中的file_path
                self.db_repo.update_file_path(conversation_id, file_path)
                
            except Exception as e:
                # 如果文件创建失败，回滚数据库操作
                logger.error(f"文件创建失败，回滚数据库: {e}")
                self.db_repo.delete(conversation_id, user_id)
                raise Exception(f"创建对话文件失败: {e}")
            
            # 4. 返回完整信息
            conversation = self.db_repo.get_by_id(conversation_id)
            if not conversation:
                raise Exception("创建后查询对话失败")
            
            return {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "title": title,
                "file_path": file_path,
                "message_count": 0,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at
            }
            
        except ValueError as e:
            logger.error(f"创建对话参数错误: {e}")
            raise
        except Exception as e:
            logger.error(f"创建对话失败: {e}")
            raise
    
    def get_conversation_list(
        self, 
        user_id: int, 
        page: int = 1, 
        page_size: int = 20
    ) -> ConversationListResponse:
        """
        获取用户的对话列表
        
        Args:
            user_id: 用户ID
            page: 页码（从1开始）
            page_size: 每页数量
            
        Returns:
            ConversationListResponse
        """
        try:
            if user_id <= 0:
                raise ValueError("user_id 必须是正整数")
            
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 20
            
            # 计算偏移量
            offset = (page - 1) * page_size
            
            # 查询对话列表
            conversations = self.db_repo.get_by_user(user_id, offset, page_size)
            
            # 查询总数
            total_count = self.db_repo.count_by_user(user_id)
            
            # 转换为字典列表
            conversation_list = [conv.to_dict() for conv in conversations]
            
            logger.info(f"获取对话列表成功: user_id={user_id}, count={len(conversations)}")
            
            return ConversationListResponse(
                conversations=conversation_list,
                total_count=total_count,
                page=page,
                page_size=page_size
            )
            
        except ValueError as e:
            logger.error(f"获取对话列表参数错误: {e}")
            raise
        except Exception as e:
            logger.error(f"获取对话列表失败: {e}")
            raise
    
    def get_conversation_detail(
        self, 
        conversation_id: int, 
        user_id: int
    ) -> ConversationDetailResponse:
        """
        获取对话详情（包含完整消息）
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            
        Returns:
            ConversationDetailResponse
            
        Raises:
            ValueError: 参数错误
            PermissionError: 权限不足
            FileNotFoundError: 对话不存在
        """
        try:
            # 验证参数
            if conversation_id <= 0 or user_id <= 0:
                raise ValueError("conversation_id 和 user_id 必须是正整数")
            
            # 1. 从数据库获取元数据
            conversation = self.db_repo.get_by_id(conversation_id)
            if not conversation:
                raise FileNotFoundError(f"对话不存在: conversation_id={conversation_id}")
            
            # 2. 验证权限
            if conversation.user_id != user_id:
                raise PermissionError(f"无权访问该对话: conversation_id={conversation_id}")
            
            # 3. 从文件读取消息
            messages = self.file_repo.read(user_id, conversation_id)
            message_list = [msg.to_dict() for msg in messages]
            
            logger.info(f"获取对话详情成功: conversation_id={conversation_id}, message_count={len(messages)}")
            
            return ConversationDetailResponse(
                conversation_id=conversation.id,
                user_id=conversation.user_id,
                title=conversation.title,
                messages=message_list,
                message_count=len(messages),
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            )
            
        except (ValueError, PermissionError, FileNotFoundError) as e:
            logger.error(f"获取对话详情失败: {e}")
            raise
        except Exception as e:
            logger.error(f"获取对话详情失败: {e}")
            raise
    
    def add_message(
        self, 
        conversation_id: int, 
        user_id: int, 
        message_data: Dict[str, Any]
    ) -> bool:
        """
        添加消息到对话
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            message_data: 消息数据字典
            
        Returns:
            是否成功
        """
        try:
            # 验证权限
            self._validate_user_permission(conversation_id, user_id)
            
            # 验证消息数据
            request = MessageAddRequest(
                role=message_data.get('role', ''),
                content=message_data.get('content', ''),
                query_mode=message_data.get('queryMode'),
                expert=message_data.get('expert'),
                steps=message_data.get('steps'),
                references=message_data.get('references')
            )
            errors = request.validate()
            if errors:
                raise ValueError(f"消息数据验证失败: {', '.join(errors)}")
            
            # 创建Message实体
            message = Message(
                role=request.role,
                content=request.content,
                timestamp=datetime.now().isoformat(),
                query_mode=request.query_mode,
                expert=request.expert,
                steps=[],  # steps会在to_dict时处理
                references=request.references or []
            )
            
            # 如果有steps数据，转换为Step实体
            if request.steps:
                from backend.models.entities import Step
                message.steps = [Step.from_dict(s) if isinstance(s, dict) else s for s in request.steps]
            
            # 1. 追加消息到文件
            self.file_repo.append_message(user_id, conversation_id, message)
            
            # 2. 更新数据库中的消息数量
            messages = self.file_repo.read(user_id, conversation_id)
            self.db_repo.update_message_count(conversation_id, len(messages))
            
            # 3. 如果是第一条用户消息，自动生成标题
            if len(messages) == 1 and message.role == 'user':
                title = self._generate_title_from_message(message.content)
                self.update_conversation_title(conversation_id, user_id, title)
            
            logger.info(f"添加消息成功: conversation_id={conversation_id}, role={message.role}")
            return True
            
        except (ValueError, PermissionError, FileNotFoundError) as e:
            logger.error(f"添加消息失败: {e}")
            raise
        except Exception as e:
            logger.error(f"添加消息失败: {e}")
            raise
    
    def update_conversation_title(
        self, 
        conversation_id: int, 
        user_id: int, 
        title: str
    ) -> bool:
        """
        更新对话标题
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            title: 新标题
            
        Returns:
            是否成功
        """
        try:
            # 验证权限
            self._validate_user_permission(conversation_id, user_id)
            
            # 验证标题
            request = ConversationUpdateRequest(title=title)
            errors = request.validate()
            if errors:
                raise ValueError(f"标题验证失败: {', '.join(errors)}")
            
            # 1. 更新数据库
            db_success = self.db_repo.update_title(conversation_id, title)
            
            # 2. 更新文件
            file_success = self.file_repo.update_title(user_id, conversation_id, title)
            
            success = db_success and file_success
            if success:
                logger.info(f"更新标题成功: conversation_id={conversation_id}")
            else:
                logger.warning(f"更新标题部分失败: db={db_success}, file={file_success}")
            
            return success
            
        except (ValueError, PermissionError, FileNotFoundError) as e:
            logger.error(f"更新标题失败: {e}")
            raise
        except Exception as e:
            logger.error(f"更新标题失败: {e}")
            raise
    
    def delete_conversation(
        self, 
        conversation_id: int, 
        user_id: int
    ) -> bool:
        """
        删除对话
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        try:
            # 验证权限
            self._validate_user_permission(conversation_id, user_id)
            
            # 1. 先删除文件
            file_success = self.file_repo.delete(user_id, conversation_id)
            if not file_success:
                logger.warning(f"删除文件失败或文件不存在: conversation_id={conversation_id}")
            
            # 2. 再删除数据库记录
            db_success = self.db_repo.delete(conversation_id, user_id)
            
            if db_success:
                logger.info(f"删除对话成功: conversation_id={conversation_id}")
            else:
                logger.warning(f"删除数据库记录失败: conversation_id={conversation_id}")
            
            return db_success
            
        except (PermissionError, FileNotFoundError) as e:
            logger.error(f"删除对话失败: {e}")
            raise
        except Exception as e:
            logger.error(f"删除对话失败: {e}")
            raise
    
    def get_conversation_count(self, user_id: int) -> int:
        """
        获取用户的对话总数
        
        Args:
            user_id: 用户ID
            
        Returns:
            对话总数
        """
        try:
            if user_id <= 0:
                raise ValueError("user_id 必须是正整数")
            
            count = self.db_repo.count_by_user(user_id)
            return count
            
        except ValueError as e:
            logger.error(f"获取对话数量参数错误: {e}")
            raise
        except Exception as e:
            logger.error(f"获取对话数量失败: {e}")
            raise
    
    def _generate_title_from_message(self, content: str) -> str:
        """
        从消息内容生成标题
        
        Args:
            content: 消息内容
            
        Returns:
            标题字符串
        """
        # 截取前30个字符
        title = content.strip()[:30]
        
        # 如果超过30字符，添加省略号
        if len(content.strip()) > 30:
            title += "..."
        
        return title if title else "新对话"
    
    def _validate_user_permission(self, conversation_id: int, user_id: int):
        """
        验证用户权限
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            
        Raises:
            ValueError: 参数错误
            FileNotFoundError: 对话不存在
            PermissionError: 权限不足
        """
        if conversation_id <= 0 or user_id <= 0:
            raise ValueError("conversation_id 和 user_id 必须是正整数")
        
        conversation = self.db_repo.get_by_id(conversation_id)
        if not conversation:
            raise FileNotFoundError(f"对话不存在: conversation_id={conversation_id}")
        
        if conversation.user_id != user_id:
            raise PermissionError(f"无权访问该对话: conversation_id={conversation_id}, user_id={user_id}")
