#!/usr/bin/env python3
"""
Marker服务测试客户端
"""

import requests
import sys
import time

# 服务地址
MARKER_SERVICE_URL = "http://localhost:8002"

def test_health():
    """测试健康检查接口"""
    print("="*60)
    print("测试1: 健康检查")
    print("="*60)
    
    try:
        response = requests.get(f"{MARKER_SERVICE_URL}/health")
        data = response.json()
        
        print(f"状态: {data['status']}")
        print(f"模型已加载: {data['model_loaded']}")
        print(f"模型加载时间: {data.get('model_load_time', 'N/A')}")
        print("✅ 健康检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_convert_pdf(pdf_path):
    """测试PDF转换接口"""
    print("\n" + "="*60)
    print("测试2: PDF转换")
    print("="*60)
    print(f"PDF文件: {pdf_path}")
    
    try:
        # 读取PDF文件
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            data = {'langs': 'en,zh'}
            
            print("发送请求...")
            start_time = time.time()
            
            response = requests.post(
                f"{MARKER_SERVICE_URL}/api/convert_pdf",
                files=files,
                data=data,
                timeout=300
            )
            
            duration = time.time() - start_time
        
        if response.ok:
            result = response.json()
            
            if result['success']:
                markdown = result['markdown']
                metadata = result['metadata']
                
                print(f"✅ 转换成功")
                print(f"处理时间: {metadata.get('processing_time', duration):.1f}秒")
                print(f"文本长度: {len(markdown)} 字符")
                print(f"页数: {metadata.get('pages', 'N/A')}")
                
                # 显示前500字符
                print("\n文本预览:")
                print("-"*60)
                print(markdown[:500])
                print("...")
                print("-"*60)
                
                return True
            else:
                print(f"❌ 转换失败: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_batch_convert(pdf_paths):
    """测试批量转换接口"""
    print("\n" + "="*60)
    print("测试3: 批量转换")
    print("="*60)
    print(f"PDF文件数: {len(pdf_paths)}")
    
    try:
        files = [('files', open(path, 'rb')) for path in pdf_paths]
        data = {'langs': 'en,zh'}
        
        print("发送请求...")
        start_time = time.time()
        
        response = requests.post(
            f"{MARKER_SERVICE_URL}/api/batch_convert",
            files=files,
            data=data,
            timeout=600
        )
        
        duration = time.time() - start_time
        
        # 关闭文件
        for _, f in files:
            f.close()
        
        if response.ok:
            result = response.json()
            
            print(f"✅ 批量转换完成")
            print(f"总耗时: {duration:.1f}秒")
            print(f"成功: {result['succeeded']}/{result['total']}")
            print(f"失败: {result['failed']}/{result['total']}")
            
            # 显示每个文件的结果
            for r in result['results']:
                status = "✅" if r['success'] else "❌"
                print(f"  {status} {r['filename']}")
                if not r['success']:
                    print(f"     错误: {r.get('error', 'Unknown')}")
            
            return True
        else:
            print(f"❌ 请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == '__main__':
    print("="*60)
    print("Marker服务测试客户端")
    print("="*60)
    
    # 测试1: 健康检查
    if not test_health():
        print("\n❌ 服务未就绪，请检查服务是否启动")
        sys.exit(1)
    
    # 测试2: 单个PDF转换
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        test_convert_pdf(pdf_path)
        
        # 测试3: 批量转换（如果提供多个文件）
        if len(sys.argv) > 2:
            test_batch_convert(sys.argv[1:])
    else:
        print("\n使用方法:")
        print("  python test_client.py <pdf_file>")
        print("  python test_client.py <pdf1> <pdf2> <pdf3>  # 批量测试")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
