#!/usr/bin/env python3
"""
Marker PDF转换服务
端口: 8002

优化版本：
- 服务启动时预加载模型（单例模式）
- 支持单个和批量PDF转换
- 并发控制（最多2个同时转换）
- 完善的错误处理和资源管理
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile
import os
import time
import logging
from datetime import datetime
import threading
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局模型和转换器变量
model_dict = None
converter = None
model_load_time = None
model_lock = threading.Lock()

def load_models():
    """加载Marker模型和转换器（单例模式）"""
    global model_dict, converter, model_load_time
    
    if converter is not None:
        return converter
    
    with model_lock:
        # 双重检查
        if converter is not None:
            return converter
        
        try:
            logger.info("🔄 正在加载Marker模型...")
            start_time = time.time()
            
            from marker.models import create_model_dict
            from marker.converters.pdf import PdfConverter
            
            # 创建模型字典
            model_dict = create_model_dict()
            
            # 创建转换器 (renderer 参数应该是字符串类名)
            converter = PdfConverter(
                artifact_dict=model_dict,
                renderer="marker.renderers.markdown.MarkdownRenderer"
            )
            
            model_load_time = datetime.now().isoformat()
            load_duration = time.time() - start_time
            
            logger.info(f"✅ 模型加载成功！耗时: {load_duration:.1f}秒")
            return converter
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

conversion_lock = threading.Semaphore(1)  # 限制并发转换数量（串行处理，避免模型冲突）

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "service": "marker-pdf-service",
        "model_loaded": converter is not None,
        "model_load_time": model_load_time,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/convert_pdf', methods=['POST'])
def convert_pdf():
    """
    PDF转Markdown接口
    
    请求参数:
        - file: PDF文件（必需）
        - langs: 语言列表，逗号分隔（可选，默认"en,zh"）
        - batch_multiplier: 批处理倍数（可选，默认2）
        - max_pages: 最大处理页数（可选，默认None=全部）
    
    响应:
        {
            "success": true,
            "markdown": "...",
            "metadata": {
                "pages": 30,
                "processing_time": 95.3
            }
        }
    """
    start_time = time.time()
    
    # 检查是否有文件
    if 'file' not in request.files:
        return jsonify({
            "success": False,
            "error": "缺少PDF文件"
        }), 400
    
    pdf_file = request.files['file']
    
    if pdf_file.filename == '':
        return jsonify({
            "success": False,
            "error": "文件名为空"
        }), 400
    
    # 获取参数
    langs = request.form.get('langs', 'en,zh').split(',')
    batch_multiplier = int(request.form.get('batch_multiplier', 2))
    max_pages = request.form.get('max_pages', None)
    if max_pages:
        max_pages = int(max_pages)
    
    # 保存到临时文件
    tmp_file = None
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf_file.save(tmp.name)
            tmp_file = tmp.name
        
        # 验证临时文件
        file_size = os.path.getsize(tmp_file)
        logger.info(f"📄 开始处理PDF: {pdf_file.filename} (大小: {file_size/1024:.1f} KB)")
        
        # 使用信号量限制并发数
        with conversion_lock:
            # 加载模型和转换器
            conv = load_models()
            
            # 使用新API转换PDF（添加重试机制）
            max_retries = 2
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    rendered = conv(tmp_file)
                    break  # 成功则跳出循环
                except RuntimeError as e:
                    last_error = e
                    if "size of tensor" in str(e) and attempt < max_retries - 1:
                        logger.warning(f"⚠️ 转换失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                        logger.info("🔄 清理缓存后重试...")
                        # 清理PyTorch缓存
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        time.sleep(1)  # 等待一秒
                    else:
                        raise
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ PDF处理成功: {pdf_file.filename}, 耗时: {processing_time:.1f}秒")
        
        # 提取 markdown 文本
        markdown_text = rendered.markdown if hasattr(rendered, 'markdown') else str(rendered)
        
        return jsonify({
            "success": True,
            "markdown": markdown_text,
            "metadata": {
                "processing_time": processing_time,
                "filename": pdf_file.filename
            }
        })
    
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)
        
        # 识别不同类型的错误
        if "PdfiumError" in str(type(e)) or "Failed to load document" in error_msg:
            # 记录更多诊断信息
            if tmp_file and os.path.exists(tmp_file):
                file_size = os.path.getsize(tmp_file)
                logger.error(f"❌ PDF文件无法解析: {pdf_file.filename} (临时文件大小: {file_size} bytes)")
                
                # 尝试用file命令检查
                try:
                    import subprocess
                    file_output = subprocess.check_output(['file', tmp_file], stderr=subprocess.STDOUT).decode()
                    logger.error(f"   文件类型检测: {file_output.strip()}")
                except:
                    pass
            else:
                logger.error(f"❌ PDF文件无法解析: {pdf_file.filename} (临时文件不存在)")
            
            logger.error(f"   原因: PDF文件损坏、加密或格式不支持")
            error_type = "PDF文件格式错误或已损坏"
        elif "size of tensor" in error_msg:
            logger.error(f"❌ 模型处理失败: {pdf_file.filename}")
            logger.error(f"   原因: 内部模型错误（已尝试重试）")
            error_type = "模型内部错误"
        else:
            logger.error(f"❌ PDF处理失败: {pdf_file.filename}, 错误: {e}")
            error_type = "未知错误"
        
        import traceback
        logger.error(traceback.format_exc())
        
        return jsonify({
            "success": False,
            "error": error_type,
            "error_detail": error_msg,
            "processing_time": processing_time
        }), 500
    
    finally:
        # 清理临时文件
        if tmp_file and os.path.exists(tmp_file):
            try:
                os.unlink(tmp_file)
            except Exception as e:
                logger.warning(f"⚠️ 清理临时文件失败: {e}")

@app.route('/api/batch_convert', methods=['POST'])
def batch_convert_pdf():
    """
    批量PDF转Markdown接口
    
    请求参数:
        - files: 多个PDF文件（必需）
        - langs: 语言列表，逗号分隔（可选，默认"en,zh"）
        - batch_multiplier: 批处理倍数（可选，默认2）
        - max_pages: 最大处理页数（可选，默认None=全部）
    
    响应:
        {
            "success": true,
            "total": 3,
            "succeeded": 2,
            "failed": 1,
            "results": [
                {
                    "filename": "paper1.pdf",
                    "success": true,
                    "markdown": "...",
                    "metadata": {...}
                },
                {
                    "filename": "paper2.pdf",
                    "success": false,
                    "error": "..."
                }
            ]
        }
    """
    start_time = time.time()
    
    # 检查是否有文件
    if 'files' not in request.files:
        return jsonify({
            "success": False,
            "error": "缺少PDF文件"
        }), 400
    
    pdf_files = request.files.getlist('files')
    
    if not pdf_files:
        return jsonify({
            "success": False,
            "error": "文件列表为空"
        }), 400
    
    # 获取参数
    langs = request.form.get('langs', 'en,zh').split(',')
    batch_multiplier = int(request.form.get('batch_multiplier', 2))
    max_pages = request.form.get('max_pages', None)
    if max_pages:
        max_pages = int(max_pages)
    
    results = []
    succeeded = 0
    failed = 0
    
    logger.info(f"📦 开始批量处理 {len(pdf_files)} 个PDF文件")
    
    # 处理每个文件
    for pdf_file in pdf_files:
        tmp_file = None
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                pdf_file.save(tmp.name)
                tmp_file = tmp.name
            
            logger.info(f"  📄 处理: {pdf_file.filename}")
            
            # 使用信号量限制并发数
            with conversion_lock:
                # 加载模型和转换器
                conv = load_models()
                
                file_start = time.time()
                # 使用新API转换（添加重试机制）
                max_retries = 2
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        rendered = conv(tmp_file)
                        break  # 成功则跳出循环
                    except RuntimeError as e:
                        last_error = e
                        if "size of tensor" in str(e) and attempt < max_retries - 1:
                            logger.warning(f"  ⚠️ 转换失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                            logger.info("  🔄 清理缓存后重试...")
                            # 清理PyTorch缓存
                            import torch
                            if torch.cuda.is_available():
                                torch.cuda.empty_cache()
                            time.sleep(1)
                        else:
                            raise
                
                file_duration = time.time() - file_start
            
            # 提取 markdown 文本
            markdown_text = rendered.markdown if hasattr(rendered, 'markdown') else str(rendered)
            
            results.append({
                "filename": pdf_file.filename,
                "success": True,
                "markdown": markdown_text,
                "metadata": {
                    "processing_time": file_duration
                }
            })
            succeeded += 1
            logger.info(f"  ✅ 完成: {pdf_file.filename}, 耗时: {file_duration:.1f}秒")
            
        except Exception as e:
            error_msg = str(e)
            
            # 识别错误类型
            if "PdfiumError" in str(type(e)) or "Failed to load document" in error_msg:
                error_type = "PDF文件格式错误或已损坏"
                logger.error(f"  ❌ PDF文件无法解析: {pdf_file.filename}")
            elif "size of tensor" in error_msg:
                error_type = "模型内部错误"
                logger.error(f"  ❌ 模型处理失败: {pdf_file.filename}")
            else:
                error_type = "未知错误"
                logger.error(f"  ❌ 失败: {pdf_file.filename}, 错误: {e}")
            
            results.append({
                "filename": pdf_file.filename,
                "success": False,
                "error": error_type,
                "error_detail": error_msg
            })
            failed += 1
        
        finally:
            # 清理临时文件
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.unlink(tmp_file)
                except Exception as e:
                    logger.warning(f"⚠️ 清理临时文件失败: {e}")
    
    total_time = time.time() - start_time
    logger.info(f"📦 批量处理完成: {succeeded}/{len(pdf_files)} 成功, 总耗时: {total_time:.1f}秒")
    
    return jsonify({
        "success": True,
        "total": len(pdf_files),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
        "total_processing_time": total_time
    })

@app.route('/', methods=['GET'])
def index():
    """简单的状态页面"""
    return jsonify({
        "service": "Marker PDF Service",
        "version": "1.0",
        "endpoints": {
            "health": "GET /health",
            "convert": "POST /api/convert_pdf",
            "batch_convert": "POST /api/batch_convert"
        }
    })

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("Marker PDF转换服务启动中...")
    logger.info("="*60)
    
    # 预加载模型
    try:
        load_models()
    except Exception as e:
        logger.error(f"❌ 模型加载失败，服务将无法处理请求: {e}")
        logger.warning("⚠️ 服务仍会启动，但需要在第一次请求时加载模型")
    
    logger.info("🎉 服务启动成功！")
    logger.info("📍 访问地址: http://0.0.0.0:8002")
    logger.info("📍 健康检查: http://0.0.0.0:8002/health")
    logger.info("📍 单个转换: POST http://0.0.0.0:8002/api/convert_pdf")
    logger.info("📍 批量转换: POST http://0.0.0.0:8002/api/batch_convert")
    logger.info("="*60)
    
    # 启动Flask服务
    app.run(
        host='0.0.0.0',
        port=8002,
        debug=False,
        threaded=True  # 支持多线程处理并发请求
    )
