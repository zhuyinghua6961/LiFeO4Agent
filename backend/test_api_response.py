"""
测试 API 返回的数据格式
"""
import sys
import os
import json

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
sys.path.insert(0, parent_dir)

from backend.database.connection import execute_query

def test_api_format():
    """测试 API 返回格式"""
    print("="*80)
    print("测试 API 返回数据格式")
    print("="*80)
    
    try:
        # 模拟 API 查询
        page_size = 10
        offset = 0
        sql = """
            SELECT id, username, role, status, user_type, created_at
            FROM users
            ORDER BY id ASC
            LIMIT %s OFFSET %s
        """
        users = execute_query(sql, (page_size, offset))
        
        # 格式化结果（模拟 API）
        data = []
        for user in users:
            formatted_user = {
                "id": user['id'],
                "username": user['username'],
                "role": user['role'],
                "user_type": user.get('user_type', 3),
                "status": user['status'],
                "created_at": user['created_at'].isoformat() if user['created_at'] else None
            }
            data.append(formatted_user)
        
        print(f"\n返回 {len(data)} 个用户:\n")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_format()
