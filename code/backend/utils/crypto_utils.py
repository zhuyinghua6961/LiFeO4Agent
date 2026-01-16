"""
加密工具模块
提供AES双向加密/解密功能
"""
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import os

# AES密钥（32字节 = 256位）- 从环境变量读取或使用默认值
AES_KEY = os.environ.get('AES_KEY', 'LifeO4Agent2024SecureKey32!!')
AES_KEY = AES_KEY[:32].ljust(32, 'X').encode('utf-8') if len(AES_KEY) < 32 else AES_KEY[:32].encode('utf-8')


def encrypt_password(password: str) -> str:
    """
    加密密码（AES-256-CBC）
    
    Args:
        password: 原始密码
        
    Returns:
        加密后的Base64编码字符串
    """
    iv = os.urandom(16)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(password.encode('utf-8'), AES.block_size))
    # 将IV和密文拼接后Base64编码
    result = base64.b64encode(iv + encrypted).decode('utf-8')
    return result


def decrypt_password(encrypted_password: str) -> str:
    """
    解密密码
    
    Args:
        encrypted_password: 加密后的Base64编码字符串
        
    Returns:
        原始密码
    """
    try:
        # Base64解码
        data = base64.b64decode(encrypted_password.encode('utf-8'))
        # 分离IV和密文
        iv = data[:16]
        encrypted = data[16:]
        # 解密
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception:
        return ""
