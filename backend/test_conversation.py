#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话持久化功能测试脚本
测试数据模型、仓储层和服务层
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
BACKEND_ROOT = Path(__file__).parent
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_entities():
    """测试实体类"""
    print("\n" + "="*60)
    print("测试 1: 实体类 (Entities)")
    print("="*60)
    
    from backend.models.entities import Conversation, Message, Step
    
    # 测试 Step
    step = Step(
        step="generate_keywords",
        message="✅ 搜索关键词生成成功",
        status="success",
        data={"keywords": "lithium iron phosphate"}
    )
    print(f"✅ Step 创建成功: {step.to_dict()}")
    
    # 测试 Message
    message = Message(
        role="user",
        content="磷酸铁锂的电压是多少？",
        timestamp=datetime.now().isoformat(),
        steps=[step],
        references=[]
    )
    print(f"✅ Message 创建成功: role={message.role}, content={message.content[:20]}...")
    
    # 测试 Conversation
    conversation = Conversation(
        id=1,
        user_id=1,
        title="测试对话",
        file_path="chat_history/user_1/conv_1.json",
        message_count=0,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    print(f"✅ Conversation 创建成功: id={conversation.id}, title={conversation.title}")
    
    # 测试验证
    errors = conversation.validate()
    if not errors:
        print("✅ Conversation 验证通过")
    else:
        print(f"❌ Conversation 验证失败: {errors}")
    
    print("\n✅ 实体类测试完成！")


def test_dtos():
    """测试 DTO 类"""
    print("\n" + "="*60)
    print("测试 2: DTO 类")
    print("="*60)
    
    from backend.models.dtos import (
        ConversationCreateRequest,
        MessageAddRequest,
        ConversationUpdateRequest
    )
    
    # 测试 ConversationCreateRequest
    create_req = ConversationCreateRequest(user_id=1, title="新对话")
    errors = create_req.validate()
    if not errors:
        print("✅ ConversationCreateRequest 验证通过")
    else:
        print(f"❌ ConversationCreateRequest 验证失败: {errors}")
    
    # 测试 MessageAddRequest
    msg_req = MessageAddRequest(
        role="user",
        content="测试消息",
        steps=[],
        references=[]
    )
    errors = msg_req.validate()
    if not errors:
        print("✅ MessageAddRequest 验证通过")
    else:
        print(f"❌ MessageAddRequest 验证失败: {errors}")
    
    # 测试 ConversationUpdateRequest
    update_req = ConversationUpdateRequest(title="更新后的标题")
    errors = update_req.validate()
    if not errors:
        print("✅ ConversationUpdateRequest 验证通过")
    else:
        print(f"❌ ConversationUpdateRequest 验证失败: {errors}")
    
    print("\n✅ DTO 类测试完成！")


def test_file_repository():
    """测试文件仓储"""
    print("\n" + "="*60)
    print("测试 3: 文件仓储 (ConversationFileRepository)")
    print("="*60)
    
    from backend.repositories.conversation_file_repository import ConversationFileRepository
    from backend.models.entities import Message
    
    file_repo = ConversationFileRepository()
    print(f"✅ 文件仓储初始化成功: {file_repo.CHAT_HISTORY_DIR}")
    
    # 测试创建对话文件
    test_user_id = 999
    test_conv_id = 1
    
    try:
        file_path = file_repo.create(test_user_id, test_conv_id, "测试对话")
        print(f"✅ 创建对话文件成功: {file_path}")
        
        # 测试文件是否存在
        exists = file_repo.exists(test_user_id, test_conv_id)
        print(f"✅ 文件存在性检查: {exists}")
        
        # 测试追加消息
        message = Message(
            role="user",
            content="这是一条测试消息",
            timestamp=datetime.now().isoformat(),
            steps=[],
            references=[]
        )
        file_repo.append_message(test_user_id, test_conv_id, message)
        print(f"✅ 追加消息成功")
        
        # 测试读取消息
        messages = file_repo.read(test_user_id, test_conv_id)
        print(f"✅ 读取消息成功: 共 {len(messages)} 条消息")
        
        # 测试更新标题
        file_repo.update_title(test_user_id, test_conv_id, "更新后的标题")
        print(f"✅ 更新标题成功")
        
        # 测试获取文件大小
        size = file_repo.get_file_size(test_user_id, test_conv_id)
        print(f"✅ 获取文件大小: {size} 字节")
        
        # 测试删除文件
        file_repo.delete(test_user_id, test_conv_id)
        print(f"✅ 删除文件成功")
        
        # 验证文件已删除
        exists = file_repo.exists(test_user_id, test_conv_id)
        print(f"✅ 文件已删除: exists={exists}")
        
    except Exception as e:
        print(f"❌ 文件仓储测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ 文件仓储测试完成！")


def test_database_repository():
    """测试数据库仓储"""
    print("\n" + "="*60)
    print("测试 4: 数据库仓储 (ConversationRepository)")
    print("="*60)
    
    from backend.repositories.conversation_repository import ConversationRepository
    
    try:
        db_repo = ConversationRepository()
        print(f"✅ 数据库仓储初始化成功")
        
        # 测试创建对话
        test_user_id = 999
        conversation_id = db_repo.create(test_user_id, "测试对话", "")
        print(f"✅ 创建对话成功: conversation_id={conversation_id}")
        
        # 测试查询对话
        conversation = db_repo.get_by_id(conversation_id)
        if conversation:
            print(f"✅ 查询对话成功: title={conversation.title}")
        else:
            print(f"❌ 查询对话失败")
        
        # 测试更新标题
        db_repo.update_title(conversation_id, "更新后的标题")
        print(f"✅ 更新标题成功")
        
        # 测试更新消息数量
        db_repo.update_message_count(conversation_id, 5)
        print(f"✅ 更新消息数量成功")
        
        # 测试查询用户对话列表
        conversations = db_repo.get_by_user(test_user_id, 0, 10)
        print(f"✅ 查询用户对话列表成功: 共 {len(conversations)} 条")
        
        # 测试统计对话数量
        count = db_repo.count_by_user(test_user_id)
        print(f"✅ 统计对话数量: {count}")
        
        # 测试检查对话存在性
        exists = db_repo.exists(conversation_id, test_user_id)
        print(f"✅ 检查对话存在性: {exists}")
        
        # 测试删除对话
        db_repo.delete(conversation_id, test_user_id)
        print(f"✅ 删除对话成功")
        
        # 验证对话已删除
        exists = db_repo.exists(conversation_id, test_user_id)
        print(f"✅ 对话已删除: exists={exists}")
        
    except Exception as e:
        print(f"❌ 数据库仓储测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ 数据库仓储测试完成！")


def test_conversation_service():
    """测试对话服务"""
    print("\n" + "="*60)
    print("测试 5: 对话服务 (ConversationService)")
    print("="*60)
    
    from backend.services.conversation_service import ConversationService
    
    try:
        service = ConversationService()
        print(f"✅ 对话服务初始化成功")
        
        test_user_id = 999
        
        # 测试创建对话
        result = service.create_conversation(test_user_id, "服务层测试对话")
        conversation_id = result['conversation_id']
        print(f"✅ 创建对话成功: conversation_id={conversation_id}")
        
        # 测试获取对话列表
        list_response = service.get_conversation_list(test_user_id, page=1, page_size=10)
        print(f"✅ 获取对话列表成功: 共 {list_response.total_count} 条")
        
        # 测试添加用户消息
        user_message = {
            'role': 'user',
            'content': '磷酸铁锂的电压是多少？',
            'steps': [],
            'references': []
        }
        service.add_message(conversation_id, test_user_id, user_message)
        print(f"✅ 添加用户消息成功")
        
        # 测试添加AI回复（带步骤）
        ai_message = {
            'role': 'assistant',
            'content': '磷酸铁锂的标准电压是3.2V...',
            'queryMode': '文献检索',
            'expert': 'literature',
            'steps': [
                {
                    'step': 'generate_keywords',
                    'message': '✅ 搜索关键词生成成功',
                    'status': 'success',
                    'data': {'keywords': 'lithium iron phosphate voltage'}
                },
                {
                    'step': 'query_vector_db',
                    'message': '✅ 找到 20 条相关文献',
                    'status': 'success',
                    'data': {'count': 20}
                }
            ],
            'references': [
                {
                    'doi': '10.1016/xxx',
                    'title': '测试文献',
                    'similarity': 0.95
                }
            ]
        }
        service.add_message(conversation_id, test_user_id, ai_message)
        print(f"✅ 添加AI回复成功（包含步骤和引用）")
        
        # 测试获取对话详情
        detail_response = service.get_conversation_detail(conversation_id, test_user_id)
        print(f"✅ 获取对话详情成功: 共 {detail_response.message_count} 条消息")
        print(f"   - 标题: {detail_response.title}")
        print(f"   - 消息数: {len(detail_response.messages)}")
        if detail_response.messages:
            first_msg = detail_response.messages[0]
            print(f"   - 第一条消息: {first_msg['role']} - {first_msg['content'][:30]}...")
            if len(detail_response.messages) > 1:
                second_msg = detail_response.messages[1]
                print(f"   - 第二条消息: {second_msg['role']} - 步骤数: {len(second_msg.get('steps', []))}")
        
        # 测试更新标题
        service.update_conversation_title(conversation_id, test_user_id, "更新后的标题")
        print(f"✅ 更新标题成功")
        
        # 测试获取对话数量
        count = service.get_conversation_count(test_user_id)
        print(f"✅ 获取对话数量: {count}")
        
        # 测试删除对话
        service.delete_conversation(conversation_id, test_user_id)
        print(f"✅ 删除对话成功")
        
    except Exception as e:
        print(f"❌ 对话服务测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ 对话服务测试完成！")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🚀 开始测试对话持久化功能")
    print("="*60)
    
    try:
        # 测试 1: 实体类
        test_entities()
        
        # 测试 2: DTO 类
        test_dtos()
        
        # 测试 3: 文件仓储
        test_file_repository()
        
        # 测试 4: 数据库仓储
        test_database_repository()
        
        # 测试 5: 对话服务（集成测试）
        test_conversation_service()
        
        print("\n" + "="*60)
        print("🎉 所有测试完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
