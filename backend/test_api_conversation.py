#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话API接口测试脚本
测试REST API端点
"""
import requests
import json

BASE_URL = "http://localhost:8000"
TEST_USER_ID = 999

# 全局token
AUTH_TOKEN = None


def login():
    """登录获取token"""
    print("\n" + "="*60)
    print("登录获取认证token")
    print("="*60)
    
    url = f"{BASE_URL}/api/auth/login"
    data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            global AUTH_TOKEN
            AUTH_TOKEN = result.get('token')
            print(f"✅ 登录成功，获取token")
            return True
        else:
            print(f"❌ 登录失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return False


def get_headers():
    """获取请求头（包含认证token）"""
    if AUTH_TOKEN:
        return {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
    return {"Content-Type": "application/json"}


def test_create_conversation():
    """测试创建对话"""
    print("\n" + "="*60)
    print("测试 1: 创建对话")
    print("="*60)
    
    url = f"{BASE_URL}/api/conversations"
    data = {
        "user_id": TEST_USER_ID,
        "title": "API测试对话"
    }
    
    response = requests.post(url, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应文本: {response.text}")
    
    try:
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except:
        print(f"无法解析JSON响应")
    
    if response.status_code == 201:
        print("✅ 创建对话成功")
        return response.json()['conversation_id']
    else:
        print("❌ 创建对话失败")
        return None


def test_get_conversation_list():
    """测试获取对话列表"""
    print("\n" + "="*60)
    print("测试 2: 获取对话列表")
    print("="*60)
    
    url = f"{BASE_URL}/api/conversations"
    params = {
        "user_id": TEST_USER_ID,
        "page": 1,
        "page_size": 10
    }
    
    response = requests.get(url, params=params)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        print("✅ 获取对话列表成功")
    else:
        print("❌ 获取对话列表失败")


def test_add_message(conversation_id):
    """测试添加消息"""
    print("\n" + "="*60)
    print("测试 3: 添加消息")
    print("="*60)
    
    # 添加用户消息
    url = f"{BASE_URL}/api/conversations/{conversation_id}/messages"
    data = {
        "user_id": TEST_USER_ID,
        "message": {
            "role": "user",
            "content": "磷酸铁锂的电压是多少？"
        }
    }
    
    response = requests.post(url, json=data)
    print(f"添加用户消息 - 状态码: {response.status_code}")
    
    if response.status_code == 201:
        print("✅ 添加用户消息成功")
    else:
        print(f"❌ 添加用户消息失败: {response.json()}")
    
    # 添加AI回复（带步骤）
    data = {
        "user_id": TEST_USER_ID,
        "message": {
            "role": "assistant",
            "content": "磷酸铁锂的标准电压是3.2V...",
            "queryMode": "文献检索",
            "expert": "literature",
            "steps": [
                {
                    "step": "generate_keywords",
                    "message": "✅ 搜索关键词生成成功",
                    "status": "success",
                    "data": {"keywords": "lithium iron phosphate voltage"}
                },
                {
                    "step": "query_vector_db",
                    "message": "✅ 找到 20 条相关文献",
                    "status": "success",
                    "data": {"count": 20}
                }
            ],
            "references": [
                {
                    "doi": "10.1016/xxx",
                    "title": "测试文献",
                    "similarity": 0.95
                }
            ]
        }
    }
    
    response = requests.post(url, json=data)
    print(f"添加AI回复 - 状态码: {response.status_code}")
    
    if response.status_code == 201:
        print("✅ 添加AI回复成功（包含步骤和引用）")
    else:
        print(f"❌ 添加AI回复失败: {response.json()}")


def test_get_conversation_detail(conversation_id):
    """测试获取对话详情"""
    print("\n" + "="*60)
    print("测试 4: 获取对话详情")
    print("="*60)
    
    url = f"{BASE_URL}/api/conversations/{conversation_id}"
    params = {"user_id": TEST_USER_ID}
    
    response = requests.get(url, params=params)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"对话标题: {data['title']}")
        print(f"消息数量: {data['message_count']}")
        print(f"消息列表:")
        for i, msg in enumerate(data['messages'], 1):
            print(f"  {i}. {msg['role']}: {msg['content'][:50]}...")
            if msg.get('steps'):
                print(f"     步骤数: {len(msg['steps'])}")
            if msg.get('references'):
                print(f"     引用数: {len(msg['references'])}")
        print("✅ 获取对话详情成功")
    else:
        print(f"❌ 获取对话详情失败: {response.json()}")


def test_update_conversation(conversation_id):
    """测试更新对话标题"""
    print("\n" + "="*60)
    print("测试 5: 更新对话标题")
    print("="*60)
    
    url = f"{BASE_URL}/api/conversations/{conversation_id}"
    data = {
        "user_id": TEST_USER_ID,
        "title": "更新后的标题"
    }
    
    response = requests.put(url, json=data)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 更新标题成功")
    else:
        print(f"❌ 更新标题失败: {response.json()}")


def test_delete_conversation(conversation_id):
    """测试删除对话"""
    print("\n" + "="*60)
    print("测试 6: 删除对话")
    print("="*60)
    
    url = f"{BASE_URL}/api/conversations/{conversation_id}"
    params = {"user_id": TEST_USER_ID}
    
    response = requests.delete(url, params=params)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 204:
        print("✅ 删除对话成功")
    else:
        print(f"❌ 删除对话失败")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🚀 开始测试对话API接口")
    print(f"服务器: {BASE_URL}")
    print("="*60)
    
    try:
        # 测试 1: 创建对话
        conversation_id = test_create_conversation()
        if not conversation_id:
            print("\n❌ 创建对话失败，终止测试")
            return
        
        # 测试 2: 获取对话列表
        test_get_conversation_list()
        
        # 测试 3: 添加消息
        test_add_message(conversation_id)
        
        # 测试 4: 获取对话详情
        test_get_conversation_detail(conversation_id)
        
        # 测试 5: 更新对话标题
        test_update_conversation(conversation_id)
        
        # 测试 6: 删除对话
        test_delete_conversation(conversation_id)
        
        print("\n" + "="*60)
        print("🎉 所有API测试完成！")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到服务器，请确保后端服务已启动")
        print(f"   启动命令: cd backend && python main.py")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
