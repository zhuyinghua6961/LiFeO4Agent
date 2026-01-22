"""
批量导入功能 - 简单测试
测试FileParser、UserDataValidator和BatchImportService
"""
import sys
import os

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
sys.path.insert(0, parent_dir)

from backend.services.file_parser import FileParser
from backend.services.user_data_validator import UserDataValidator


def test_file_parser():
    """测试文件解析器"""
    print("="*80)
    print("测试1: FileParser - 文件解析")
    print("="*80)
    
    parser = FileParser()
    
    # 测试CSV解析
    try:
        csv_path = os.path.join(backend_dir, 'test_batch_import_sample.csv')
        df = parser.parse_file(csv_path, 'csv')
        print(f"✅ CSV文件解析成功")
        print(f"   记录数: {len(df)}")
        print(f"   列名: {list(df.columns)}")
        print(f"\n前3行数据:")
        print(df.head(3))
        return df
    except Exception as e:
        print(f"❌ CSV文件解析失败: {e}")
        return None


def test_user_data_validator(df):
    """测试数据验证器"""
    print("\n" + "="*80)
    print("测试2: UserDataValidator - 数据验证")
    print("="*80)
    
    validator = UserDataValidator()
    
    # 测试第一条记录
    if df is not None and len(df) > 0:
        row = df.iloc[0]
        username = row['username']
        password = row['password']
        user_type = row['user_type']
        
        print(f"\n测试数据: username={username}, password={password}, user_type={user_type}")
        
        # 验证用户名
        is_valid, msg = validator.validate_username(username)
        print(f"  用户名验证: {'✅ 通过' if is_valid else '❌ 失败'} - {msg if not is_valid else '有效'}")
        
        # 验证密码
        is_valid, msg = validator.validate_password(password)
        print(f"  密码验证: {'✅ 通过' if is_valid else '❌ 失败'} - {msg if not is_valid else '有效'}")
        
        # 验证用户身份
        is_valid, msg = validator.validate_user_type(user_type)
        print(f"  用户身份验证: {'✅ 通过' if is_valid else '❌ 失败'} - {msg if not is_valid else '有效'}")
        
        # 映射用户身份
        user_type_code = validator.map_user_type_to_code(user_type)
        print(f"  用户身份映射: {user_type} → {user_type_code}")
        
        # 完整验证
        is_valid, msg = validator.validate_user_data(username, password, user_type)
        print(f"\n  完整验证: {'✅ 通过' if is_valid else '❌ 失败'} - {msg if not is_valid else '所有字段有效'}")


def test_invalid_data():
    """测试无效数据"""
    print("\n" + "="*80)
    print("测试3: 无效数据验证")
    print("="*80)
    
    validator = UserDataValidator()
    
    test_cases = [
        ("ab", "Pass123!", "common", "用户名太短"),
        ("testuser", "12345", "common", "密码太短"),
        ("testuser", "Pass123!", "admin", "不允许导入管理员"),
        ("admin123", "Pass123!", "common", "用户名以admin开头"),
    ]
    
    for username, password, user_type, desc in test_cases:
        is_valid, msg = validator.validate_user_data(username, password, user_type)
        status = "❌ 正确拒绝" if not is_valid else "⚠️  错误通过"
        print(f"  {status}: {desc}")
        print(f"    输入: username={username}, password={password}, user_type={user_type}")
        print(f"    结果: {msg}")


if __name__ == "__main__":
    print("\n🧪 批量导入功能 - 简单测试\n")
    
    # 测试1: 文件解析
    df = test_file_parser()
    
    # 测试2: 数据验证
    test_user_data_validator(df)
    
    # 测试3: 无效数据
    test_invalid_data()
    
    print("\n" + "="*80)
    print("✅ 测试完成")
    print("="*80)
