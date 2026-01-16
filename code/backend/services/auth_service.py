"""
认证服务
处理用户登录、注册、密码验证、JWT Token生成
"""
import bcrypt
import jwt
import time
from datetime import datetime
from typing import Optional, Dict, Any
from backend.config.settings import settings
from backend.database.connection import execute_query, execute_update


class AuthService:
    """认证服务类"""
    
    def __init__(self):
        self.jwt_secret = settings.jwt_secret
        self.jwt_expire = settings.jwt_expire
    
    def hash_password(self, password: str) -> str:
        """
        加密密码
        
        Args:
            password: 原始密码
            
        Returns:
            加密后的密码
        """
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """
        验证密码
        
        Args:
            password: 原始密码
            hashed: 加密后的密码
            
        Returns:
            是否匹配
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_token(self, user_id: int, role: str) -> str:
        """
        创建JWT Token
        
        Args:
            user_id: 用户ID
            role: 用户角色
            
        Returns:
            JWT Token
        """
        payload = {
            "user_id": user_id,
            "role": role,
            "exp": time.time() + self.jwt_expire,
            "iat": time.time()
        }
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        解析JWT Token
        
        Args:
            token: JWT Token
            
        Returns:
            解析后的payload，失败返回None
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            用户信息，失败返回None
        """
        sql = "SELECT id, username, password, role, status, created_at FROM users WHERE username = %s"
        results = execute_query(sql, (username,))
        return results[0] if results else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        根据ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户信息，失败返回None
        """
        sql = "SELECT id, username, role, status, created_at FROM users WHERE id = %s"
        results = execute_query(sql, (user_id,))
        return results[0] if results else None
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            登录结果
        """
        # 获取用户
        user = self.get_user_by_username(username)
        if not user:
            return {
                "success": False,
                "error": "用户名或密码错误",
                "code": "INVALID_CREDENTIALS"
            }
        
        # 检查账号状态
        if user['status'] == 'disabled':
            return {
                "success": False,
                "error": "账号已被停用，请联系管理员",
                "code": "ACCOUNT_DISABLED"
            }
        
        # 验证密码
        if not self.verify_password(password, user['password']):
            return {
                "success": False,
                "error": "用户名或密码错误",
                "code": "INVALID_CREDENTIALS"
            }
        
        # 生成Token
        token = self.create_token(user['id'], user['role'])
        
        return {
            "success": True,
            "message": "登录成功",
            "data": {
                "token": token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "role": user['role']
                }
            }
        }
    
    def register(self, username: str, password: str) -> Dict[str, Any]:
        """
        用户注册
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            注册结果
        """
        # 检查用户名是否已存在
        existing = self.get_user_by_username(username)
        if existing:
            return {
                "success": False,
                "error": "用户名已被注册",
                "code": "USERNAME_EXISTS"
            }
        
        # 加密密码
        hashed_password = self.hash_password(password)
        
        # 插入用户
        sql = """
            INSERT INTO users (username, password, role, status)
            VALUES (%s, %s, 'user', 'active')
        """
        user_id = execute_update(sql, (username, hashed_password))
        
        return {
            "success": True,
            "message": "注册成功",
            "data": {
                "id": user_id,
                "username": username,
                "role": "user"
            }
        }
    
    def get_user_info(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户信息
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "code": "USER_NOT_FOUND"
            }
        
        return {
            "success": True,
            "data": {
                "id": user['id'],
                "username": user['username'],
                "role": user['role'],
                "status": user['status'],
                "created_at": user['created_at'].isoformat() if user['created_at'] else None
            }
        }
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict[str, Any]:
        """
        修改密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            
        Returns:
            修改结果
        """
        # 获取用户
        sql = "SELECT id, password FROM users WHERE id = %s"
        results = execute_query(sql, (user_id,))
        if not results:
            return {
                "success": False,
                "error": "用户不存在",
                "code": "USER_NOT_FOUND"
            }
        
        user = results[0]
        
        # 验证旧密码
        if not self.verify_password(old_password, user['password']):
            return {
                "success": False,
                "error": "旧密码错误",
                "code": "INVALID_PASSWORD"
            }
        
        # 更新密码
        hashed_password = self.hash_password(new_password)
        sql = "UPDATE users SET password = %s WHERE id = %s"
        execute_update(sql, (hashed_password, user_id))
        
        return {
            "success": True,
            "message": "密码修改成功"
        }


# 全局服务实例
auth_service = AuthService()
