"""
API路由定义
RESTful API端点
"""
import json
import logging
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify
from flask_cors import CORS

from backend.config.settings import settings
from backend.services.llm_service import LLMService
from backend.services.neo4j_service import Neo4jService
from backend.services.vector_service import VectorService
from backend.agents.experts import RouterExpert, QueryExpert, SemanticExpert
from backend.models import (
    QueryRequest, RouteRequest, SearchParams,
    QueryResponse, RouteResponse, SearchResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

# 创建蓝图
api = Blueprint('api', __name__, url_prefix='/api')

# 全局服务实例（懒加载）
_llm_service: Optional[LLMService] = None
_neo4j_service: Optional[Neo4jService] = None
_vector_service: Optional[VectorService] = None
_router_expert: Optional[RouterExpert] = None
_query_expert: Optional[QueryExpert] = None
_semantic_expert: Optional[SemanticExpert] = None


def get_services():
    """获取所有服务实例（懒加载）"""
    global _llm_service, _neo4j_service, _vector_service
    global _router_expert, _query_expert, _semantic_expert
    
    if _llm_service is None:
        _llm_service = LLMService(
            api_key=settings.llm_api_key,
            model=settings.llm_model
        )
    
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    
    if _vector_service is None:
        from backend.repositories.vector_repository import VectorRepository, CommunityVectorRepository
        vector_repo = VectorRepository()
        community_repo = CommunityVectorRepository()
        _vector_service = VectorService(
            vector_repo=vector_repo,
            community_repo=community_repo,
            llm_service=_llm_service
        )
    
    if _router_expert is None:
        _router_expert = RouterExpert(llm_service=_llm_service)
    
    if _query_expert is None:
        _query_expert = QueryExpert(
            neo4j_service=_neo4j_service,
            llm_service=_llm_service
        )
    
    if _semantic_expert is None:
        from backend.repositories.vector_repository import VectorRepository
        vector_repo = VectorRepository()
        _semantic_expert = SemanticExpert(
            vector_repo=vector_repo,
            llm_service=_llm_service
        )
    
    return {
        'llm': _llm_service,
        'neo4j': _neo4j_service,
        'vector': _vector_service,
        'router': _router_expert,
        'query': _query_expert,
        'semantic': _semantic_expert
    }


# ============== 问答流式端点 (RAG 模式) ==============

@api.route('/ask_stream', methods=['POST'])
def ask_stream():
    """
    问答流式接口 (SSE格式) - 使用 IntegratedAgent
    
    流程:
    1. 用户提问
    2. IntegratedAgent 自动路由到合适的专家
    3. 专家执行查询并合成答案
    4. 流式返回结果
    5. (可选) 保存对话到持久化存储
    
    请求体:
    {
        "question": "磷酸铁锂的电压是多少",
        "chat_history": [],
        "user_id": 1 (可选),
        "conversation_id": 123 (可选)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify(ErrorResponse(error='请求体不能为空', code='INVALID_REQUEST').to_dict()), 400
    
    question = data.get('question', '')
    if not question:
        return jsonify(ErrorResponse(error='问题不能为空', code='VALIDATION_ERROR').to_dict()), 400
    
    # 获取可选的持久化参数
    user_id = data.get('user_id')
    conversation_id = data.get('conversation_id')
    
    logger.info(f"🔍 收到问题: {question}, user_id={user_id}, conversation_id={conversation_id}")
    
    def generate():
        nonlocal conversation_id  # 声明使用外层的 conversation_id 变量
        
        # 用于收集AI回复的完整数据
        collected_steps = []
        collected_content = ""
        collected_references = []
        expert_used = None
        query_mode = None
        
        try:
            # 获取 IntegratedAgent
            from backend.agents.integrated_agent import get_integrated_agent
            integrated_agent = get_integrated_agent()
            
            # 如果提供了user_id但没有conversation_id，自动创建新对话
            if user_id and not conversation_id:
                try:
                    from backend.services.conversation_service import ConversationService
                    conv_service = ConversationService()
                    result = conv_service.create_conversation(user_id, "新对话")
                    conversation_id = result['conversation_id']
                    logger.info(f"自动创建新对话: conversation_id={conversation_id}")
                except Exception as e:
                    logger.warning(f"自动创建对话失败: {e}")
            
            # 如果启用持久化，保存用户消息
            if user_id and conversation_id:
                try:
                    from backend.services.conversation_service import ConversationService
                    conv_service = ConversationService()
                    user_message = {
                        'role': 'user',
                        'content': question,
                        'steps': [],
                        'references': []
                    }
                    conv_service.add_message(conversation_id, user_id, user_message)
                    logger.info(f"保存用户消息成功: conversation_id={conversation_id}")
                except Exception as e:
                    logger.warning(f"保存用户消息失败: {e}")
            
            # 发送开始信号
            start_data = json.dumps({'type': 'start', 'message': '开始处理问题'}, ensure_ascii=False)
            yield f"data: {start_data}\n\n"
            
            # 使用 IntegratedAgent 流式查询
            for chunk in integrated_agent.query_stream(question):
                # 收集数据用于持久化
                if chunk.get('type') == 'step':
                    collected_steps.append({
                        'step': chunk.get('step'),
                        'message': chunk.get('message'),
                        'status': chunk.get('status'),
                        'data': chunk.get('data'),
                        'error': chunk.get('error')
                    })
                elif chunk.get('type') == 'content':
                    collected_content += chunk.get('content', '')
                elif chunk.get('type') == 'done':
                    collected_references = chunk.get('references', [])
                    if chunk.get('metadata'):
                        expert_used = chunk.get('metadata', {}).get('expert')
                
                # 流式输出
                chunk_data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {chunk_data}\n\n"
            
            # 如果启用持久化，保存AI回复
            if user_id and conversation_id and collected_content:
                try:
                    from backend.services.conversation_service import ConversationService
                    conv_service = ConversationService()
                    
                    # 确定查询模式
                    if expert_used == 'neo4j':
                        query_mode = '知识图谱'
                    elif expert_used == 'community':
                        query_mode = '社区分析'
                    else:
                        query_mode = '文献检索'
                    
                    ai_message = {
                        'role': 'assistant',
                        'content': collected_content,
                        'queryMode': query_mode,
                        'expert': expert_used,
                        'steps': collected_steps,
                        'references': collected_references
                    }
                    conv_service.add_message(conversation_id, user_id, ai_message)
                    logger.info(f"保存AI回复成功: conversation_id={conversation_id}, steps={len(collected_steps)}")
                except Exception as e:
                    logger.warning(f"保存AI回复失败: {e}")
            
            # 发送完成信号
            done_data = json.dumps({'type': 'done', 'message': '回答完成'}, ensure_ascii=False)
            yield f"data: {done_data}\n\n"
            
        except Exception as e:
            logger.error(f"❌ 处理问题时出错: {e}", exc_info=True)
            error_data = json.dumps({
                'type': 'error',
                'error': str(e),
                'message': '处理问题时发生错误'
            }, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
    
    return generate(), {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}


# ============== PDF 文件服务 ==============

@api.route('/pdf/<path:filename>', methods=['GET'])
def serve_pdf(filename):
    """提供 PDF 文件访问 - 通过DOI映射查找实际PDF文件"""
    from flask import send_from_directory
    import os
    import json
    
    logger.info(f"📄 收到PDF请求: {filename}")
    
    # 使用 settings 中配置的路径
    from backend.config.settings import settings
    
    pdf_dir = settings.papers_dir
    mapping_file = settings.doi_to_pdf_mapping
    
    logger.debug(f"   PDF目录: {pdf_dir}")
    logger.debug(f"   映射文件: {mapping_file}")
    
    # 从filename提取DOI
    doi = filename.replace('.pdf', '').replace('_', '/')
    logger.info(f"   提取DOI: {doi}")
    
    # 尝试通过DOI映射查找实际文件名
    real_filename = None
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                doi_mapping = json.load(f)
                logger.debug(f"   映射文件包含 {len(doi_mapping)} 个DOI")
                if doi in doi_mapping:
                    real_filename = doi_mapping[doi]
                    logger.info(f"   ✅ 通过映射找到: {doi} -> {real_filename}")
                else:
                    logger.warning(f"   ⚠️ 映射中未找到DOI: {doi}")
        except Exception as e:
            logger.error(f"   ❌ 读取映射文件失败: {e}")
    else:
        logger.warning(f"   ⚠️ 映射文件不存在: {mapping_file}")
    
    # 如果找到映射，使用真实文件名
    if real_filename:
        pdf_path = os.path.join(pdf_dir, real_filename)
        logger.debug(f"   检查映射文件路径: {pdf_path}")
        if os.path.exists(pdf_path):
            logger.info(f"   ✅ 返回PDF文件: {real_filename}")
            return send_from_directory(pdf_dir, real_filename)
        else:
            logger.warning(f"   ⚠️ 映射的PDF文件不存在: {real_filename}")
    
    # 如果没有映射或文件不存在，尝试直接用filename查找
    pdf_path = os.path.join(pdf_dir, filename)
    logger.debug(f"   尝试直接访问: {pdf_path}")
    if os.path.exists(pdf_path):
        logger.info(f"   ✅ 直接找到PDF: {filename}")
        return send_from_directory(pdf_dir, filename)
    
    # 都找不到，返回404
    logger.error(f"   ❌ PDF文件未找到: DOI={doi}, filename={filename}")
    return jsonify({
        'error': 'PDF_NOT_FOUND',
        'message': '本地PDF文件不存在',
        'doi': doi,
        'filename': filename,
        'suggestion': '您可以尝试在线查看该文献'
    }), 404


# ============== 知识库信息 ==============

@api.route('/kb_info', methods=['GET'])
def kb_info():
    """获取知识库信息"""
    try:
        from backend.repositories.vector_repository import VectorRepository, CommunityVectorRepository
        
        vector_repo = VectorRepository()
        community_repo = CommunityVectorRepository()
        
        literature_count = vector_repo.get_count()
        community_count = community_repo.get_count()
        
        return jsonify({
            "success": True,
            "kb_size": literature_count + community_count,
            "source_stats": {
                "neo4j": False,
                "chromadb": True
            },
            "collections": {
                "literature": literature_count,
                "community": community_count
            }
        })
        
    except Exception as e:
        logger.error(f"获取知识库信息失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============== 翻译服务 ==============

@api.route('/translate', methods=['POST'])
def translate():
    """
    翻译文本
    
    请求体:
    {
        "texts": ["text1", "text2", ...]
    }
    """
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        
        if not texts:
            return jsonify({'error': '文本列表为空'}), 400
        
        # 获取LLM服务
        from backend.services import get_llm_service
        llm_service = get_llm_service()
        
        # 翻译每个文本
        translations = []
        for text in texts:
            if not text or not text.strip():
                translations.append("")
                continue
            
            try:
                # 构建翻译提示
                from langchain_core.messages import HumanMessage, SystemMessage
                messages = [
                    SystemMessage(content="你是专业的学术论文翻译专家。请将英文文献翻译成准确、流畅的中文，保持专业术语的准确性。"),
                    HumanMessage(content=f"请将以下英文翻译成中文：\n\n{text}\n\n要求：\n1. 只输出翻译结果，不要添加任何说明、注释或解释\n2. 不要输出关于翻译规范、翻译特点的说明\n3. 保持专业术语准确，译文通顺")
                ]
                
                # 调用LLM
                response = llm_service.invoke(messages)
                translation = response.content.strip()
                translations.append(translation)
                
            except Exception as e:
                logger.error(f"翻译失败: {e}")
                translations.append(f"翻译失败: {str(e)}")
        
        return jsonify({
            'translations': translations,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"翻译服务错误: {e}")
        return jsonify({'error': str(e)}), 500


# ============== 健康检查 ==============

@api.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    services = get_services()
    
    status = {
        "status": "healthy" if all([
            services['llm'] is not None,
            services['neo4j'] is not None,
            services['vector'] is not None
        ]) else "degraded",
        "services": {
            "llm": services['llm'] is not None,
            "neo4j": services['neo4j'] is not None,
            "vector": services['vector'] is not None,
            "router": services['router'] is not None,
            "query": services['query'] is not None,
            "semantic": services['semantic'] is not None
        },
        "version": "1.0.0"
    }
    
    return jsonify(status)


# ============== 路由端点 ==============

@api.route('/route', methods=['POST'])
def route_question():
    """路由查询到合适的专家系统"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="请求体不能为空",
                code="INVALID_REQUEST"
            ).to_dict()), 400
        
        req = RouteRequest(question=data.get('question', ''))
        errors = req.validate()
        if errors:
            return jsonify(ErrorResponse(
                error="; ".join(errors),
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        services = get_services()
        result = services['router'].route(req.question)
        
        return jsonify(RouteResponse(
            primary_expert=result.get('primary_expert', ''),
            confidence=result.get('confidence', 0.0),
            reasoning=result.get('reasoning', ''),
            secondary_expert=result.get('secondary_expert'),
            query_type=result.get('query_type'),
            suggested_keywords=result.get('suggested_keywords', [])
        ).to_dict())
        
    except Exception as e:
        logger.error(f"路由失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="ROUTE_ERROR"
        ).to_dict()), 500


# ============== 查询端点 ==============

@api.route('/query', methods=['POST'])
def execute_query():
    """执行查询"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="请求体不能为空",
                code="INVALID_REQUEST"
            ).to_dict()), 400
        
        question = data.get('question', '')
        expert = data.get('expert')
        top_k = data.get('top_k', 10)
        
        if not question:
            return jsonify(ErrorResponse(
                error="问题不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        services = get_services()
        
        if expert is None:
            route_result = services['router'].route(question)
            expert = route_result.get('primary_expert', 'literature')
        
        if expert == 'neo4j':
            result = services['query'].execute_query(question)
            expert_type = "neo4j"
        else:
            result = services['semantic'].search(question, top_k=top_k)
            expert_type = "literature"
        
        if result.get('success'):
            response = QueryResponse(
                success=True,
                answer=f"找到 {result.get('result_count', 0)} 条结果",
                expert_type=expert_type,
                sources=result.get('materials', []) or result.get('documents', []),
                metadata={
                    "question": question,
                    "expert": expert,
                    "cypher_query": result.get('cypher_query'),
                    "search_query": result.get('search_query')
                }
            )
        else:
            response = QueryResponse(
                success=False,
                answer=f"查询失败: {result.get('error', '未知错误')}",
                expert_type=expert_type,
                error=result.get('error')
            )
        
        return jsonify(response.to_dict())
        
    except Exception as e:
        logger.error(f"查询失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="QUERY_ERROR"
        ).to_dict()), 500


# ============== 精确查询端点 ==============

@api.route('/query/material', methods=['POST'])
def query_material():
    """材料精确查询"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="请求体不能为空",
                code="INVALID_REQUEST"
            ).to_dict()), 400
        
        property_name = data.get('property', '')
        threshold = data.get('threshold', 0)
        comparison = data.get('comparison', '>')
        limit = data.get('limit', 100)
        
        if not property_name:
            return jsonify(ErrorResponse(
                error="属性名不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        services = get_services()
        materials = services['query'].query_by_property(
            property_name=property_name,
            threshold=threshold,
            comparison=comparison,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "property": property_name,
            "threshold": threshold,
            "comparison": comparison,
            "materials": materials,
            "count": len(materials)
        })
        
    except Exception as e:
        logger.error(f"材料查询失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="QUERY_ERROR"
        ).to_dict()), 500


# ============== 语义搜索端点 ==============

@api.route('/search', methods=['POST'])
def search_documents():
    """语义搜索"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="请求体不能为空",
                code="INVALID_REQUEST"
            ).to_dict()), 400
        
        query = data.get('query', '')
        top_k = data.get('top_k', 10)
        collection = data.get('collection', 'literature')
        
        if not query:
            return jsonify(ErrorResponse(
                error="查询不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        services = get_services()
        
        if collection == 'community':
            result = services['vector'].search_community(query, top_k=top_k)
        else:
            result = services['vector'].search_literature(query, top_k=top_k)
        
        return jsonify(SearchResponse(
            success=result.get('success', False),
            query=query,
            documents=result.get('documents', result.get('communities', [])),
            total_count=result.get('total_count', 0),
            search_time_ms=result.get('search_time_ms', 0),
            error=result.get('error')
        ).to_dict())
        
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="SEARCH_ERROR"
        ).to_dict()), 500


# ============== 聚合知识端点 ==============

@api.route('/aggregate', methods=['POST'])
def aggregate_knowledge():
    """聚合知识"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="请求体不能为空",
                code="INVALID_REQUEST"
            ).to_dict()), 400
        
        query = data.get('query', '')
        literature_k = data.get('literature_k', 10)
        community_k = data.get('community_k', 5)
        
        if not query:
            return jsonify(ErrorResponse(
                error="查询不能为空",
                code="VALIDATION_ERROR"
            ).to_dict()), 400
        
        services = get_services()
        result = services['vector'].aggregate_knowledge(
            query=query,
            literature_k=literature_k,
            community_k=community_k
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"聚合知识失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="AGGREGATION_ERROR"
        ).to_dict()), 500


# ============== 统计端点 ==============

@api.route('/stats', methods=['GET'])
def get_stats():
    """获取数据库统计信息"""
    try:
        services = get_services()
        
        literature_stats = services['vector'].get_collection_stats('literature')
        community_stats = services['vector'].get_collection_stats('community')
        
        return jsonify({
            "success": True,
            "statistics": {
                "literature": {
                    "count": literature_stats.get('count', 0)
                },
                "community": {
                    "count": community_stats.get('count', 0)
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify(ErrorResponse(
            error=str(e),
            code="STATS_ERROR"
        ).to_dict()), 500


# ============== 错误处理 ==============

@api.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify(ErrorResponse(
        error="请求的资源不存在",
        code="NOT_FOUND"
    ).to_dict()), 404


@api.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify(ErrorResponse(
        error="服务器内部错误",
        code="INTERNAL_ERROR"
    ).to_dict()), 500
