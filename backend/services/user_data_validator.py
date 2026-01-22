"""
用户数据验证服务
用于验证批量导入的用户数据
"""
from typing import Tuple, Set, List
from backend.database.connection import execute_query


class UserDataValidator:
    """用户数据验证工具类"""
    
    def __init__(self):
        """初始化验证器"""
        pass
    
    def validate_username(self, username: str) -> Tuple[bool, str]:
        """
        验证用户名
        
        Args:
            username: 用户名
            
        Returns:
            (是否有效, 错误消息)
        """
        # 检查是否为空
        if not username or username == 'nan' or username.strip() == '':
            return False, "用户名不能为空"
        
        # 检查长度
        if len(username) < 3 or len(username) > 50:
            return False, "用户名长度必须在3-50之间"
        
        # 检查是否以admin开头
        if username.lower().startswith('admin'):
            return False, "用户名不能以admin开头"
        
        return True, ""
    
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """
        验证密码（与管理员添加账号要求一致）
        
        Args:
            password: 密码
            
        Returns:
            (是否有效, 错误消息)
        """
        # 检查是否为空
        if not password or password == 'nan' or password.strip() == '':
            return False, "密码不能为空"
        
        # 检查长度（与管理员添加账号一致：至少6位）
        if len(password) < 6:
            return False, "密码长度不能少于6位"
        
        return True, ""
    
    def validate_user_type(self, user_type: str) -> Tuple[bool, str]:
        """
        验证用户身份
        
        Args:
            user_type: 用户身份（super或common）
            
        Returns:
            (是否有效, 错误消息)
        """
        # 检查是否为空
        if not user_type or user_type == 'nan' or user_type.strip() == '':
            return False, "用户身份不能为空"
        
        # 检查是否为有效值
        user_type_lower = user_type.lower()
        if user_type_lower not in ('super', 'common'):
            return False, "用户身份必须是super或common，不允许导入管理员"
        
        return True, ""
    
    def map_user_type_to_code(self, user_type: str) -> int:
        """
        将用户身份字符串映射为数字编码
        
        Args:
            user_type: 用户身份字符串（super或common）
            
        Returns:
            用户身份编码（2=超级用户，3=普通用户，0=无效）
        """
        mapping = {
            'super': 2,
            'common': 3
        }
        return mapping.get(user_type.lower(), 0)
    
    def validate_user_data(self, username: str, password: str, user_type: str) -> Tuple[bool, str]:
        """
        验证单条用户数据
        
        Args:
            username: 用户名
            password: 密码
            user_type: 用户身份
            
        Returns:
            (是否有效, 错误消息)
        """
        # 验证用户名
        is_valid, error_msg = self.validate_username(username)
        if not is_valid:
            return False, error_msg
        
        # 验证密码
        is_valid, error_msg = self.validate_password(password)
        if not is_valid:
            return False, error_msg
        
        # 验证用户身份
        is_valid, error_msg = self.validate_user_type(user_type)
        if not is_valid:
            return False, error_msg
        
        return True, ""
    
    def check_duplicate_in_file(self, usernames: List[str]) -> Set[str]:
        """
        检查文件中重复的用户名
        
        Args:
            usernames: 用户名列表
            
        Returns:
            重复的用户名集合
        """
        seen = set()
        duplicates = set()
        
        for username in usernames:
            if username in seen:
                duplicates.add(username)
            else:
                seen.add(username)
        
        return duplicates
    
    def check_existing_users(self, usernames: List[str]) -> Set[str]:
        """
        批量查询数据库中已存在的用户名
        
        Args:
            usernames: 用户名列表
            
        Returns:
            已存在的用户名集合
        """
        if not usernames:
            return set()
        
        try:
            # 构建IN查询
            placeholders = ','.join(['%s'] * len(usernames))
            sql = f"SELECT username FROM users WHERE username IN ({placeholders})"
            
            results = execute_query(sql, tuple(usernames))
            
            # 提取已存在的用户名
            existing = {row['username'] for row in results}
            return existing
        except Exception as e:
            # 如果查询失败，返回空集合（不阻塞导入流程）
            print(f"查询已存在用户失败: {e}")
            return set()
