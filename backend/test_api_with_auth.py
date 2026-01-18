#!/usr/bin/env python3
"""
测试对话API（带认证）
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def get_auth_token(username="zyh", password="zhuyinghua123.."):
    """登录获取 token"""
    print(f"\n1. 登录获取 token (用户: {username})...")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": username, "password": password}
    )
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            token = data['data']['token']
            user_id = data['data']['user']['id']
            print(f"   ✅ 登录成功，用户ID: {user_id}")
            return token, user_id
    
    print(f"   ❌ 登录失败: {response.text}")
    return None, None


def test_conversation_apis(token, user_id):
    """测试对话相关API"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n" + "="*60)
    print("测试对话API")
    print("="*60)
    
    # 2. 创建对话
    print("\n2. 创建对话...")
    response = requests.post(
        f"{BASE_URL}/api/conversations",
        headers=headers,
        json={"user_id": user_id, "title": "测试对话"}
    )
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.text}")
    
    if response.status_code != 201:
        print("   ❌ 创建失败")
        return
    
    conv_data = response.json()
    conversation_id = conv_data.get('conversation_id') or conv_data.get('id')
    print(f"   ✅ 创建成功，对话ID: {conversation_id}")
    
    # 3. 获取对话列表
    print("\n3. 获取对话列表...")
    response = requests.get(
        f"{BASE_URL}/api/conversations",
        headers=headers,
        params={"user_id": user_id}
    )
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        # 兼容不同的返回格式
        if isinstance(data, dict):
            if 'data' in data:
                conv_list = data['data']
            elif 'conversations' in data:
                conv_list = data['conversations']
            else:
                conv_list = []
            print(f"   ✅ 获取成功，共 {len(conv_list)} 个对话")
            if conv_list:
                print(f"   第一个对话: {conv_list[0].get('title', 'N/A')}")
        else:
            print(f"   ✅ 获取成功")
    else:
        print(f"   ❌ 获取失败: {response.text}")
    
    # 4. 添加用户消息
    print("\n4. 添加用户消息...")
    response = requests.post(
        f"{BASE_URL}/api/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "user_id": user_id,
            "message": {
                "role": "user",
                "content": "你好，这是一条测试消息"
            }
        }
    )
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 201:
        print("   ✅ 添加成功")
    else:
        print(f"   ❌ 添加失败: {response.text}")
    
    # 5. 添加AI回复（带步骤和引用）
    print("\n5. 添加AI回复（带步骤和引用）...")
    response = requests.post(
        f"{BASE_URL}/api/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "user_id": user_id,
            "message": {
                "role": "bot",
                "content": "你好！我是AI助手。",
                "queryMode": "知识图谱",
                "expert": "neo4j",
                "steps": [
                    {
                        "step": "query_analysis",
                        "message": "分析查询意图",
                        "status": "success",
                        "data": {"count": 1}
                    },
                    {
                        "step": "knowledge_retrieval",
                        "message": "检索知识图谱",
                        "status": "success",
                        "data": {"count": 5}
                    }
                ],
                "references": [
                    {
                        "title": "测试文献1",
                        "doi": "10.1234/test1"
                    }
                ]
            }
        }
    )
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 201:
        print("   ✅ 添加成功")
    else:
        print(f"   ❌ 添加失败: {response.text}")
    
    # 6. 获取对话详情
    print("\n6. 获取对话详情...")
    response = requests.get(
        f"{BASE_URL}/api/conversations/{conversation_id}",
        headers=headers,
        params={"user_id": user_id}
    )
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        # 兼容不同的返回格式
        messages = data.get('messages', [])
        msg_count = len(messages)
        print(f"   ✅ 获取成功，共 {msg_count} 条消息")
        
        # 验证步骤和引用是否保存
        for i, msg in enumerate(messages):
            print(f"   消息 {i+1}: {msg['role']} - {msg['content'][:30]}...")
            if msg['role'] in ['bot', 'assistant']:
                steps = msg.get('steps', [])
                refs = msg.get('references', [])
                print(f"      步骤数: {len(steps)}, 引用数: {len(refs)}")
                if steps:
                    print(f"      第一个步骤: {steps[0]}")
                if refs:
                    print(f"      第一个引用: {refs[0]}")
    else:
        print(f"   ❌ 获取失败: {response.text}")
    
    # 7. 更新对话标题
    print("\n7. 更新对话标题...")
    response = requests.put(
        f"{BASE_URL}/api/conversations/{conversation_id}",
        headers=headers,
        json={
            "user_id": user_id,
            "title": "更新后的标题"
        }
    )
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ 更新成功")
    else:
        print(f"   ❌ 更新失败: {response.text}")
    
    # 8. 删除对话（注释掉以保留数据查看）
    print("\n8. 删除对话...")
    print("   ⏭️  跳过删除，保留数据以供查看")
    # response = requests.delete(
    #     f"{BASE_URL}/api/conversations/{conversation_id}",
    #     headers=headers,
    #     params={"user_id": user_id}
    # )
    # print(f"   状态码: {response.status_code}")
    # 
    # if response.status_code in [200, 204]:
    #     print("   ✅ 删除成功")
    # else:
    #     print(f"   ❌ 删除失败: {response.text}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    # 获取 token
    token, user_id = get_auth_token()
    
    if token and user_id:
        # 测试对话API
        test_conversation_apis(token, user_id)
    else:
        print("\n❌ 无法获取认证token，测试终止")
