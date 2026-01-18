#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的对话API测试
"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("="*60)
print("测试对话API（无需认证）")
print("="*60)

# 测试1: 创建对话
print("\n1. 创建对话...")
url = f"{BASE_URL}/api/conversations"
data = {"user_id": 999, "title": "测试对话"}
response = requests.post(url, json=data)
print(f"   状态码: {response.status_code}")
print(f"   响应: {response.text[:200]}")

if response.status_code == 201:
    result = response.json()
    conv_id = result['conversation_id']
    print(f"   ✅ 创建成功: conversation_id={conv_id}")
    
    # 测试2: 获取对话列表
    print("\n2. 获取对话列表...")
    url = f"{BASE_URL}/api/conversations?user_id=999"
    response = requests.get(url)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 获取成功: 共{result['total_count']}条对话")
    
    # 测试3: 添加消息
    print("\n3. 添加消息...")
    url = f"{BASE_URL}/api/conversations/{conv_id}/messages"
    data = {
        "user_id": 999,
        "message": {
            "role": "user",
            "content": "测试消息"
        }
    }
    response = requests.post(url, json=data)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 201:
        print(f"   ✅ 添加成功")
    
    # 测试4: 获取对话详情
    print("\n4. 获取对话详情...")
    url = f"{BASE_URL}/api/conversations/{conv_id}?user_id=999"
    response = requests.get(url)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 获取成功: {result['message_count']}条消息")
    
    # 测试5: 删除对话
    print("\n5. 删除对话...")
    url = f"{BASE_URL}/api/conversations/{conv_id}?user_id=999"
    response = requests.delete(url)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 204:
        print(f"   ✅ 删除成功")
else:
    print(f"   ❌ 创建失败")

print("\n" + "="*60)
print("测试完成")
print("="*60)
