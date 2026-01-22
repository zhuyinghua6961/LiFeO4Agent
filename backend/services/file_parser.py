"""
文件解析服务
用于解析Excel和CSV文件
"""
import pandas as pd
from typing import Tuple


class FileParser:
    """文件解析工具类"""
    
    def __init__(self):
        """初始化文件解析器"""
        self.required_columns = ['username', 'password', 'user_type']
    
    def parse_excel(self, file_path: str) -> pd.DataFrame:
        """
        解析Excel文件
        
        Args:
            file_path: Excel文件路径
            
        Returns:
            DataFrame包含用户数据
            
        Raises:
            ValueError: 文件解析失败或格式错误
        """
        try:
            # 读取Excel文件（只读第一个sheet）
            df = pd.read_excel(file_path, sheet_name=0)
            return df
        except Exception as e:
            raise ValueError(f"Excel文件解析失败: {str(e)}")
    
    def parse_csv(self, file_path: str) -> pd.DataFrame:
        """
        解析CSV文件（支持UTF-8和GBK编码）
        
        Args:
            file_path: CSV文件路径
            
        Returns:
            DataFrame包含用户数据
            
        Raises:
            ValueError: 文件解析失败或格式错误
        """
        try:
            # 尝试UTF-8编码
            df = pd.read_csv(file_path, encoding='utf-8')
            return df
        except UnicodeDecodeError:
            try:
                # 尝试GBK编码
                df = pd.read_csv(file_path, encoding='gbk')
                return df
            except Exception as e:
                raise ValueError(f"CSV文件解析失败（尝试了UTF-8和GBK编码）: {str(e)}")
        except Exception as e:
            raise ValueError(f"CSV文件解析失败: {str(e)}")
    
    def validate_columns(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        验证DataFrame是否包含必需的列
        
        Args:
            df: 待验证的DataFrame
            
        Returns:
            (是否有效, 错误消息)
        """
        missing_columns = [col for col in self.required_columns if col not in df.columns]
        
        if missing_columns:
            return False, f"缺少必需列: {', '.join(missing_columns)}"
        
        return True, ""
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗数据：去除空行、去除首尾空格
        
        Args:
            df: 待清洗的DataFrame
            
        Returns:
            清洗后的DataFrame
        """
        # 去除完全为空的行
        df = df.dropna(how='all')
        
        # 转换为字符串并去除首尾空格
        df['username'] = df['username'].astype(str).str.strip()
        df['password'] = df['password'].astype(str).str.strip()
        df['user_type'] = df['user_type'].astype(str).str.strip().str.lower()
        
        return df
    
    def parse_file(self, file_path: str, file_type: str) -> pd.DataFrame:
        """
        解析文件（统一入口）
        
        Args:
            file_path: 文件路径
            file_type: 文件类型（xlsx或csv）
            
        Returns:
            DataFrame包含用户数据
            
        Raises:
            ValueError: 文件解析失败或格式错误
        """
        # 解析文件
        if file_type == 'xlsx':
            df = self.parse_excel(file_path)
        elif file_type == 'csv':
            df = self.parse_csv(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")
        
        # 验证必需列
        is_valid, error_msg = self.validate_columns(df)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 清洗数据
        df = self.clean_data(df)
        
        # 检查是否为空
        if len(df) == 0:
            raise ValueError("文件为空或不包含有效数据行")
        
        return df
