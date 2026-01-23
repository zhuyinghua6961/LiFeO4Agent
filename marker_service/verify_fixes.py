#!/usr/bin/env python3
"""
验证修复脚本 - 检查server.py的关键修复点
"""

import ast
import sys

def check_server_py():
    """检查server.py的修复情况"""
    print("="*60)
    print("验证 marker_service/server.py 的修复")
    print("="*60)
    
    with open('server.py', 'r', encoding='utf-8') as f:
        content = f.read()
        tree = ast.parse(content)
    
    checks = {
        "threading导入": "import threading" in content,
        "模型全局变量": all(x in content for x in ['model_lst', 'model_loaded', 'model_load_time']),
        "模型锁定义": "model_lock = threading.Lock()" in content,
        "并发控制信号量": "conversion_lock = threading.Semaphore" in content,
        "load_models函数": "def load_models():" in content,
        "健康检查返回model_loaded": '"model_loaded": model_loaded' in content,
        "批量转换接口": "def batch_convert_pdf():" in content,
        "/api/batch_convert路由": "@app.route('/api/batch_convert'" in content,
        "启动时预加载模型": "load_models()" in content and "__name__ == '__main__'" in content,
        "使用预加载模型": "model_lst=model_lst" in content,
        "并发锁使用": "with conversion_lock:" in content,
    }
    
    all_passed = True
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有检查通过！")
        print("="*60)
        return 0
    else:
        print("⚠️ 部分检查未通过，请检查代码")
        print("="*60)
        return 1

if __name__ == '__main__':
    sys.exit(check_server_py())
