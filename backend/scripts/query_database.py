"""
数据库查询脚本
用于查询和分析数据库内容
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.connection import get_connection, execute_query
from backend.config.settings import settings
import pymysql


def print_separator(title=""):
    """打印分隔线"""
    if title:
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print('=' * 80)
    else:
        print('-' * 80)


def show_tables():
    """显示所有表"""
    print_separator("数据库中的所有表")
    
    try:
        tables = execute_query("SHOW TABLES")
        
        if not tables:
            print("❌ 数据库中没有表")
            return []
        
        table_names = []
        for i, table in enumerate(tables, 1):
            table_name = list(table.values())[0]
            table_names.append(table_name)
            print(f"{i}. {table_name}")
        
        return table_names
    except Exception as e:
        print(f"❌ 查询表失败: {e}")
        return []


def describe_table(table_name: str):
    """显示表结构"""
    print_separator(f"表结构: {table_name}")
    
    try:
        columns = execute_query(f"DESCRIBE {table_name}")
        
        if not columns:
            print(f"❌ 表 {table_name} 不存在或没有列")
            return
        
        # 打印表头
        print(f"{'字段名':<20} {'类型':<20} {'NULL':<8} {'键':<8} {'默认值':<15} {'额外':<15}")
        print_separator()
        
        # 打印每一列
        for col in columns:
            field = col.get('Field', '')
            type_ = col.get('Type', '')
            null = col.get('Null', '')
            key = col.get('Key', '')
            default = str(col.get('Default', '')) if col.get('Default') is not None else 'NULL'
            extra = col.get('Extra', '')
            
            print(f"{field:<20} {type_:<20} {null:<8} {key:<8} {default:<15} {extra:<15}")
        
    except Exception as e:
        print(f"❌ 查询表结构失败: {e}")


def count_records(table_name: str):
    """统计表记录数"""
    try:
        result = execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        count = result[0]['count'] if result else 0
        return count
    except Exception as e:
        print(f"❌ 统计记录数失败: {e}")
        return 0


def query_users():
    """查询用户表"""
    print_separator("用户表 (users) 数据")
    
    try:
        # 先检查表是否存在
        tables = execute_query("SHOW TABLES LIKE 'users'")
        if not tables:
            print("❌ users 表不存在")
            return
        
        # 查询表结构
        describe_table('users')
        
        # 统计记录数
        count = count_records('users')
        print(f"\n📊 总记录数: {count}")
        
        if count == 0:
            print("⚠️  表中没有数据")
            return
        
        # 查询所有用户
        print_separator("所有用户数据")
        users = execute_query("SELECT * FROM users ORDER BY id")
        
        if not users:
            print("⚠️  没有查询到用户数据")
            return
        
        # 打印用户信息
        for i, user in enumerate(users, 1):
            print(f"\n用户 {i}:")
            for key, value in user.items():
                # 隐藏密码
                if key == 'password_hash':
                    value = '***' if value else None
                print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"❌ 查询用户失败: {e}")
        import traceback
        traceback.print_exc()


def query_conversations():
    """查询对话表"""
    print_separator("对话表 (conversations) 数据")
    
    try:
        # 先检查表是否存在
        tables = execute_query("SHOW TABLES LIKE 'conversations'")
        if not tables:
            print("❌ conversations 表不存在")
            return
        
        # 查询表结构
        describe_table('conversations')
        
        # 统计记录数
        count = count_records('conversations')
        print(f"\n📊 总记录数: {count}")
        
        if count == 0:
            print("⚠️  表中没有数据")
            return
        
        # 查询最近10条对话
        print_separator("最近10条对话")
        conversations = execute_query("""
            SELECT * FROM conversations 
            ORDER BY updated_at DESC 
            LIMIT 10
        """)
        
        if not conversations:
            print("⚠️  没有查询到对话数据")
            return
        
        # 打印对话信息
        for i, conv in enumerate(conversations, 1):
            print(f"\n对话 {i}:")
            for key, value in conv.items():
                print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"❌ 查询对话失败: {e}")
        import traceback
        traceback.print_exc()


def query_user_conversations(user_id: int):
    """查询指定用户的对话"""
    print_separator(f"用户 {user_id} 的对话")
    
    try:
        conversations = execute_query("""
            SELECT * FROM conversations 
            WHERE user_id = %s
            ORDER BY updated_at DESC
        """, (user_id,))
        
        if not conversations:
            print(f"⚠️  用户 {user_id} 没有对话记录")
            return
        
        print(f"📊 总对话数: {len(conversations)}")
        
        for i, conv in enumerate(conversations, 1):
            print(f"\n对话 {i}:")
            print(f"  ID: {conv['id']}")
            print(f"  标题: {conv['title']}")
            print(f"  消息数: {conv['message_count']}")
            print(f"  创建时间: {conv['created_at']}")
            print(f"  更新时间: {conv['updated_at']}")
            print(f"  文件路径: {conv['file_path']}")
        
    except Exception as e:
        print(f"❌ 查询用户对话失败: {e}")


def main():
    """主函数"""
    print("=" * 80)
    print("  数据库查询工具")
    print("=" * 80)
    print(f"\n数据库配置:")
    print(f"  Host: {settings.mysql_host}")
    print(f"  Port: {settings.mysql_port}")
    print(f"  Database: {settings.mysql_database}")
    print(f"  User: {settings.mysql_user}")
    
    try:
        # 测试连接
        conn = get_connection()
        print("\n✅ 数据库连接成功")
        
        # 显示所有表
        tables = show_tables()
        
        if not tables:
            print("\n⚠️  数据库中没有表，请先创建表结构")
            return
        
        # 查询用户表
        if 'users' in tables:
            query_users()
        else:
            print("\n⚠️  users 表不存在")
        
        # 查询对话表
        if 'conversations' in tables:
            query_conversations()
        else:
            print("\n⚠️  conversations 表不存在")
        
        print("\n" + "=" * 80)
        print("  查询完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 数据库连接失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
