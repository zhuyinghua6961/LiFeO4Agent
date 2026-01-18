#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API端点测试脚本
Test API Endpoints
"""
import requests
import json
import time

API_BASE = "http://localhost:5000/api"


def print_section(title):
    """打印分节标题"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_health():
    """测试健康检查"""
    print_section("测试1: 健康检查")
    
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        data = response.json()
        
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_kb_info():
    """测试知识库信息"""
    print_section("测试2: 知识库信息")
    
    try:
        response = requests.get(f"{API_BASE}/kb_info", timeout=10)
        data = response.json()
        
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 知识库大小: {data.get('kb_size')}")
        print(f"✅ 文献数量: {data.get('collections', {}).get('literature', 0)}")
        print(f"✅ 社区摘要: {data.get('collections', {}).get('community', 0)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_route():
    """测试路由功能"""
    print_section("测试3: 问题路由")
    
    test_questions = [
        "振实密度大于2.8的材料有哪些？",  # 应该路由到 neo4j
        "有哪些关于碳包覆LiFePO4的研究？",  # 应该路由到 literature
        "LiFePO4材料的社区研究有哪些？"  # 应该路由到 community
    ]
    
    for question in test_questions:
        try:
            print(f"\n问题: {question}")
            response = requests.post(
                f"{API_BASE}/route",
                json={"question": question},
                timeout=10
            )
            data = response.json()
            
            if data.get("success"):
                print(f"  ✅ 专家: {data.get('expert')}")
                print(f"  ✅ 置信度: {data.get('confidence'):.2f}")
                print(f"  ✅ 原因: {data.get('reasoning', 'N/A')[:50]}...")
            else:
                print(f"  ❌ 失败: {data.get('error')}")
                return False
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            return False
    
    print("\n✅ 所有路由测试通过")
    return True


def test_search():
    """测试向量搜索"""
    print_section("测试4: 向量搜索")
    
    try:
        response = requests.post(
            f"{API_BASE}/search",
            json={
                "query": "LiFePO4 电化学性能",
                "top_k": 5
            },
            timeout=15
        )
        data = response.json()
        
        if data.get("success"):
            print(f"✅ 找到 {data.get('count')} 条结果")
            results = data.get('results', [])
            if results:
                print(f"✅ 第一条结果预览: {results[0].get('content', '')[:100]}...")
            return True
        else:
            print(f"❌ 搜索失败: {data.get('error')}")
            return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_ask_stream():
    """测试流式问答"""
    print_section("测试5: 流式问答 (SSE)")
    
    try:
        print("\n问题: 振实密度大于2.8的材料有哪些？")
        print("正在流式接收响应...")
        print("-"*60)
        
        response = requests.post(
            f"{API_BASE}/ask_stream",
            json={"question": "振实密度大于2.8的材料有哪些？"},
            stream=True,
            timeout=60
        )
        
        chunk_count = 0
        content_chunks = []
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    try:
                        data = json.loads(data_str)
                        msg_type = data.get('type')
                        
                        if msg_type == 'start':
                            print(f"▶️  开始处理问题")
                        elif msg_type == 'thinking':
                            print(f"🤔 {data.get('content')}")
                        elif msg_type == 'metadata':
                            print(f"📊 专家: {data.get('expert')}, 置信度: {data.get('confidence', 0):.2f}")
                        elif msg_type == 'content':
                            content = data.get('content', '')
                            print(content, end='', flush=True)
                            content_chunks.append(content)
                            chunk_count += 1
                        elif msg_type == 'done':
                            print(f"\n✅ 回答完成 (共 {chunk_count} 个片段)")
                        elif msg_type == 'error':
                            print(f"\n❌ 错误: {data.get('error')}")
                            return False
                    except json.JSONDecodeError:
                        pass
        
        print("-"*60)
        print(f"✅ 流式问答测试通过 (接收 {chunk_count} 个内容片段)")
        return chunk_count > 0
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有API测试"""
    print("\n" + "🧪 " + "="*58)
    print("   API端点测试")
    print("   请确保后端服务已启动: python main.py")
    print("="*60)
    
    # 检查服务是否运行
    try:
        requests.get("http://localhost:5000/", timeout=3)
    except:
        print("\n❌ 无法连接到后端服务 (http://localhost:5000)")
        print("   请先启动服务: cd code/backend && python main.py")
        return 1
    
    results = []
    
    # 运行测试
    results.append(("健康检查", test_health()))
    results.append(("知识库信息", test_kb_info()))
    results.append(("问题路由", test_route()))
    results.append(("向量搜索", test_search()))
    results.append(("流式问答", test_ask_stream()))
    
    # 统计结果
    print_section("测试结果汇总")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print("-"*60)
    print(f"总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有API测试通过！")
        return 0
    else:
        print(f"\n⚠️ 部分测试失败 ({passed}/{total})")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
