"""
数据库连接模块
提供MySQL数据库连接
"""
import pymysql
from typing import Optional
from backend.config.settings import settings

# 全局连接池
_pool: Optional[pymysql.connections.Connection] = None


def get_connection() -> pymysql.connections.Connection:
    """
    获取数据库连接（单例模式）
    
    Returns:
        MySQL连接对象
    """
    global _pool
    
    if _pool is None or not _pool.open:
        _pool = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
    
    return _pool


def close_connection():
    """关闭数据库连接"""
    global _pool
    if _pool is not None and _pool.open:
        _pool.close()
        _pool = None


def execute_query(sql: str, params: tuple = None) -> list:
    """
    执行查询
    
    Args:
        sql: SQL语句
        params: 参数
        
    Returns:
        查询结果列表
    """
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def execute_update(sql: str, params: tuple = None) -> int:
    """
    执行更新（插入/更新/删除）
    
    Args:
        sql: SQL语句
        params: 参数
        
    Returns:
        影响行数
    """
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.lastrowid if cursor.lastrowid else cursor.rowcount


if __name__ == "__main__":
    # 测试连接
    try:
        conn = get_connection()
        print("✅ 数据库连接成功")
        conn.close()
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
