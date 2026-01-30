#!/usr/bin/env python3
"""
本地 BGE Embedding 服务
兼容 OpenAI API 格式
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from typing import List
import uvicorn
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BGE Embedding Service",
    description="本地 BGE 中文 Embedding 服务",
    version="1.0.0"
)

# 全局模型实例
model = None

class EmbeddingRequest(BaseModel):
    input: List[str]
    model: str = "bge-large-zh-v1.5"

class EmbeddingResponse(BaseModel):
    data: List[dict]
    model: str
    usage: dict

@app.on_event("startup")
async def load_model():
    """启动时加载模型"""
    global model
    try:
        logger.info("正在加载 BGE 模型: BAAI/bge-large-zh-v1.5")
        model = SentenceTransformer(
            'BAAI/bge-large-zh-v1.5',
            device='cuda'  # 使用 GPU,如果没有改为 'cpu'
        )
        logger.info("✅ 模型加载完成!")
    except Exception as e:
        logger.error(f"❌ 模型加载失败: {e}")
        # 尝试 CPU 模式
        logger.info("尝试使用 CPU 模式...")
        model = SentenceTransformer(
            'BAAI/bge-large-zh-v1.5',
            device='cpu'
        )
        logger.info("✅ 模型加载完成 (CPU 模式)")

@app.post("/v1/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    """
    生成文本的 embedding 向量
    
    兼容 OpenAI API 格式:
    POST /v1/embeddings
    {
        "input": ["文本1", "文本2"]
    }
    """
    if model is None:
        raise HTTPException(status_code=503, detail="模型未加载")
    
    try:
        logger.info(f"收到请求: {len(request.input)} 个文本")
        
        # 生成 embeddings
        embeddings = model.encode(
            request.input,
            normalize_embeddings=True,  # L2 归一化
            show_progress_bar=False,
            batch_size=128  # 批处理大小
        )
        
        # 格式化响应
        data = [
            {
                "object": "embedding",
                "embedding": embedding.tolist(),
                "index": i
            }
            for i, embedding in enumerate(embeddings)
        ]
        
        logger.info(f"✅ 成功生成 {len(data)} 个 embeddings")
        
        return EmbeddingResponse(
            data=data,
            model="bge-large-zh-v1.5",
            usage={
                "prompt_tokens": sum(len(text.split()) for text in request.input),
                "total_tokens": sum(len(text.split()) for text in request.input)
            }
        )
    
    except Exception as e:
        logger.error(f"❌ Embedding 生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy" if model is not None else "unhealthy",
        "model": "bge-large-zh-v1.5",
        "device": str(model.device) if model else "unknown",
        "embedding_dim": 1024
    }

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "BGE Embedding Service",
        "model": "BAAI/bge-large-zh-v1.5",
        "version": "1.0.0",
        "endpoints": {
            "embeddings": "/v1/embeddings",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BGE Embedding 服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8001, help="监听端口")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数")
    args = parser.parse_args()
    
    logger.info(f"🚀 启动 BGE Embedding 服务")
    logger.info(f"   监听地址: {args.host}:{args.port}")
    logger.info(f"   工作进程: {args.workers}")
    
    uvicorn.run(
        "bge_server:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level="info"
    )
