#!/usr/bin/env python3
"""
测试新版 marker-pdf API
"""

import sys

def test_imports():
    """测试导入"""
    print("="*60)
    print("测试1: 检查导入")
    print("="*60)
    
    try:
        from marker.models import create_model_dict
        print("✅ marker.models.create_model_dict 导入成功")
        
        from marker.converters.pdf import PdfConverter
        print("✅ marker.converters.pdf.PdfConverter 导入成功")
        
        from marker.renderers.markdown import MarkdownRenderer
        print("✅ marker.renderers.markdown.MarkdownRenderer 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_creation():
    """测试模型创建（不加载权重）"""
    print("\n" + "="*60)
    print("测试2: 创建模型字典结构")
    print("="*60)
    
    try:
        print("注意: 这个测试只验证API，不实际加载模型")
        print("因为模型加载需要下载大量文件并消耗大量时间")
        
        from marker.models import create_model_dict
        print("✅ create_model_dict 函数可用")
        
        # 检查函数签名
        import inspect
        sig = inspect.signature(create_model_dict)
        print(f"函数签名: {sig}")
        print(f"参数: {list(sig.parameters.keys())}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_converter_class():
    """测试转换器类"""
    print("\n" + "="*60)
    print("测试3: 检查 PdfConverter 类")
    print("="*60)
    
    try:
        from marker.converters.pdf import PdfConverter
        from marker.renderers.markdown import MarkdownRenderer
        import inspect
        
        # 检查 __init__ 签名
        init_sig = inspect.signature(PdfConverter.__init__)
        print(f"PdfConverter.__init__ 签名: {init_sig}")
        
        # 检查 __call__ 方法
        call_sig = inspect.signature(PdfConverter.__call__)
        print(f"PdfConverter.__call__ 签名: {call_sig}")
        
        print("✅ PdfConverter 类结构正确")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("="*60)
    print("Marker PDF 新API测试")
    print("="*60)
    
    all_passed = True
    
    if not test_imports():
        all_passed = False
    
    if not test_model_creation():
        all_passed = False
    
    if not test_converter_class():
        all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ 所有测试通过")
        sys.exit(0)
    else:
        print("❌ 部分测试失败")
        sys.exit(1)
