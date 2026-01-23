#!/usr/bin/env python3
"""
Marker PDF转换服务
端口: 8002

简化版本：不预加载模型，每次请求时让Marker自己处理
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile
import os
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "service": "marker-pdf-service",
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
        
        logger.info(f"📄 开始处理PDF: {pdf_file.filename}")
        
        # 使用Marker处理
        from marker.convert import convert_single_pdf
        from marker.models import load_all_models
        
        # 加载模型并转换
        model_lst = load_all_models()
        full_text, images, out_meta = convert_single_pdf(
            tmp_file,
            model_lst=model_lst,
            langs=langs,
            batch_multiplier=batch_multiplier,
            max_pages=max_pages
        )
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ PDF处理成功: {pdf_file.filename}, 耗时: {processing_time:.1f}秒")
        
        return jsonify({
            "success": True,
            "markdown": full_text,
            "metadata": {
                **out_meta,
                "processing_time": processing_time,
                "filename": pdf_file.filename
            }
        })
    
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ PDF处理失败: {pdf_file.filename}, 错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return jsonify({
            "success": False,
            "error": str(e),
            "processing_time": processing_time
        }), 500
    
    finally:
        # 清理临时文件
        if tmp_file and os.path.exists(tmp_file):
            try:
                os.unlink(tmp_file)
            except Exception as e:
                logger.warning(f"⚠️ 清理临时文件失败: {e}")

@app.route('/', methods=['GET'])
def index():
    """简单的状态页面"""
    return jsonify({
        "service": "Marker PDF Service",
        "version": "1.0",
        "endpoints": {
            "health": "GET /health",
            "convert": "POST /api/convert_pdf"
        }
    })

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("Marker PDF转换服务启动中...")
    logger.info("="*60)
    logger.info("🎉 服务启动成功！")
    logger.info("📍 访问地址: http://0.0.0.0:8002")
    logger.info("📍 健康检查: http://0.0.0.0:8002/health")
    logger.info("="*60)
    
    # 启动Flask服务
    app.run(
        host='0.0.0.0',
        port=8002,
        debug=False,
        threaded=True  # 支持多线程处理并发请求
    )
