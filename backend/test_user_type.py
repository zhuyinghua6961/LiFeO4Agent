"""
测试 user_type 字段
"""
import sys
import os

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
sys.path.insert(0, parent_dir)

from backend.database.connection import execute_query

def test_user_type():
    """测试用户类型字段"""
    print("="*80)
    print("测试 user_type 字段")
    print("="*80)
    
    try:
        # 查询所有用户
        sql = "SELECT id, username, role, user_type FROM users ORDER BY id"
        users = execute_query(sql)
        
        print(f"\n找到 {len(users)} 个用户:\n")
        print(f"{'ID':<6} {'用户名':<20} {'Role':<10} {'UserType':<10}")
        print("-" * 80)
        
        for user in users:
            user_id = user['id']
            username = user['username']
            role = user.get('role', 'N/A')
            user_type = user.get('user_type', 'NULL')
            
            print(f"{user_id:<6} {username:<20} {role:<10} {user_type}")
        
        print("\n" + "="*80)
        print("说明:")
        print("  user_type = 1: 管理员")
        print("  user_type = 2: 超级用户")
        print("  user_type = 3: 普通用户")
        print("  user_type = NULL: 未设置")
        print("="*80)
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_user_type()
