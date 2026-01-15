#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后端主入口
使用新架构的Flask应用
"""
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径（确保 backend 模块可以被导入）
BACKEND_ROOT = Path(__file__).parent
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from flask import Flask, jsonify
from flask_cors import CORS
from backend.config.settings import settings
from backend.api.routes import api
from backend.services import get_llm_service, get_neo4j_service, get_vector_service


def create_app() -> Flask:
    """
    创建Flask应用
    
    Returns:
        Flask应用实例
    """
    app = Flask(__name__)
    
    # 启用 CORS（允许所有跨域请求）
    CORS(app, origins="*", supports_credentials=False)
    
    # 注册蓝图
    app.register_blueprint(api)
    
    # 根路由
    @app.route('/')
    def index():
        return jsonify({
            "name": "Material Knowledge Base API",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "health": "/api/health",
                "route": "/api/route",
                "query": "/api/query",
                "search": "/api/search",
                "aggregate": "/api/aggregate",
                "stats": "/api/stats"
            }
        })
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": {
                "message": "请求的资源不存在",
                "code": "NOT_FOUND"
            }
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "success": False,
            "error": {
                "message": "服务器内部错误",
                "code": "INTERNAL_ERROR"
            }
        }), 500
    
    return app


def initialize_services() -> bool:
    """
    初始化服务
    
    Returns:
        是否成功（Neo4j 可选）
    """
    try:
        logger.info("🔧 正在初始化服务...")
        
        # 初始化LLM服务
        llm = get_llm_service()
        logger.info("✅ LLM服务初始化完成")
        
        # Neo4j服务（可选）
        try:
            neo4j = get_neo4j_service()
            logger.info("✅ Neo4j服务初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ Neo4j服务初始化失败（可选）: {e}")
        
        # 初始化向量服务
        try:
            vector = get_vector_service()
            logger.info("✅ 向量服务初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ 向量服务初始化失败（可选）: {e}")
        
        logger.info("🎉 服务初始化完成！（Neo4j/向量服务为可选）")
        return True
        
    except Exception as e:
        logger.error(f"❌ LLM服务初始化失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 材料知识库后端服务")
    print("=" * 60)
    
    # 初始化服务
    if not initialize_services():
        logger.error("服务初始化失败，退出")
        sys.exit(1)
    
    # 创建应用
    app = create_app()
    
    # 获取配置
    host = settings.api_host
    port = settings.api_port
    debug = settings.debug
    
    print("\n" + "-" * 60)
    print(f"📡 服务启动中...")
    print(f"   地址: http://{host}:{port}")
    print(f"   调试模式: {'开启' if debug else '关闭'}")
    print("-" * 60 + "\n")
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n👋 服务已停止")


if __name__ == "__main__":
    main()
