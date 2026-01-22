"""
检查 users 表结构
"""
import sys
import os

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
sys.path.insert(0, parent_dir)

from backend.database.connection import execute_query

def check_table():
    """检查表结构"""
    print("="*80)
    print("检查 users 表结构")
    print("="*80)
    
    try:
        result = execute_query('DESCRIBE users')
        print("\n字段列表:\n")
        for r in result:
            print(f"  {r['Field']:<20} {r['Type']:<20} {r['Null']:<10} {r['Key']:<10} {r.get('Default', 'NULL')}")
        
        # 检查是否有 user_type 字段
        fields = [r['Field'] for r in result]
        if 'user_type' in fields:
            print("\n✅ user_type 字段存在")
        else:
            print("\n❌ user_type 字段不存在！需要执行迁移脚本：")
            print("   mysql -u root -p < backend/database/add_user_type.sql")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_table()
