"""
批量导入服务
用于批量导入用户账号
"""
import time
import pandas as pd
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from backend.services.user_data_validator import UserDataValidator
from backend.services.auth_service import auth_service
from backend.database.connection import execute_update, execute_query


@dataclass
class ImportResult:
    """单条记录的导入结果"""
    row: int                    # 行号（从1开始，表头为第1行）
    username: str               # 用户名
    status: str                 # 状态：success/failed/skipped
    message: str                # 结果消息
    user_id: int = None         # 创建成功时的用户ID


@dataclass
class BatchImportResult:
    """批量导入结果"""
    total: int                  # 总记录数
    success: int                # 成功数
    failed: int                 # 失败数
    skipped: int                # 跳过数
    details: List[Dict]         # 详细结果
    duration: float             # 导入耗时（秒）


class BatchImportService:
    """批量导入服务类"""
    
    def __init__(self):
        """初始化批量导入服务"""
        self.validator = UserDataValidator()
    
    def process_single_user(
        self,
        row_num: int,
        username: str,
        password: str,
        user_type: str,
        existing_usernames: set,
        seen_usernames: set
    ) -> ImportResult:
        """
        处理单条用户记录
        
        Args:
            row_num: 行号
            username: 用户名
            password: 密码
            user_type: 用户身份
            existing_usernames: 数据库中已存在的用户名
            seen_usernames: 文件中已处理的用户名
            
        Returns:
            导入结果
        """
        # 数据验证
        is_valid, error_msg = self.validator.validate_user_data(username, password, user_type)
        if not is_valid:
            return ImportResult(
                row=row_num,
                username=username,
                status='skipped',
                message=error_msg
            )
        
        # 检查用户名是否已存在于数据库
        if username in existing_usernames:
            return ImportResult(
                row=row_num,
                username=username,
                status='skipped',
                message='用户名已存在'
            )
        
        # 检查文件中是否重复
        if username in seen_usernames:
            return ImportResult(
                row=row_num,
                username=username,
                status='skipped',
                message='文件中存在重复用户名'
            )
        
        # 创建用户
        try:
            # 将用户身份映射为数字编码
            user_type_code = self.validator.map_user_type_to_code(user_type)
            
            # 加密密码
            encrypted_password = auth_service.encrypt_password(password)
            
            # 插入数据库
            sql = """
                INSERT INTO users (username, password, role, status, user_type, created_at)
                VALUES (%s, %s, 'user', 'active', %s, NOW())
            """
            user_id = execute_update(sql, (username, encrypted_password, user_type_code))
            
            # 标记为已处理
            seen_usernames.add(username)
            existing_usernames.add(username)
            
            return ImportResult(
                row=row_num,
                username=username,
                status='success',
                message='创建成功',
                user_id=user_id
            )
        except Exception as e:
            return ImportResult(
                row=row_num,
                username=username,
                status='failed',
                message=f'创建失败: {str(e)}'
            )
    
    def import_users(self, df: pd.DataFrame) -> BatchImportResult:
        """
        批量导入用户（主流程）
        
        Args:
            df: 包含用户数据的DataFrame
            
        Returns:
            批量导入结果
        """
        start_time = time.time()
        results = []
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        # 检查记录数限制
        if len(df) > 1000:
            raise ValueError("记录数超限，单次最多导入1000条记录")
        
        # 获取数据库中已存在的用户名
        all_usernames = df['username'].tolist()
        existing_usernames = self.validator.check_existing_users(all_usernames)
        
        # 用于跟踪文件中已处理的用户名
        seen_usernames = set()
        
        # 逐行处理
        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel行号（从2开始，因为第1行是表头）
            username = row['username']
            password = row['password']
            user_type = row['user_type']
            
            result = self.process_single_user(
                row_num,
                username,
                password,
                user_type,
                existing_usernames,
                seen_usernames
            )
            
            results.append(result)
            
            # 统计
            if result.status == 'success':
                success_count += 1
            elif result.status == 'failed':
                failed_count += 1
            elif result.status == 'skipped':
                skipped_count += 1
        
        duration = time.time() - start_time
        
        # 转换为字典列表
        details = [asdict(r) for r in results]
        
        return BatchImportResult(
            total=len(df),
            success=success_count,
            failed=failed_count,
            skipped=skipped_count,
            details=details,
            duration=duration
        )
