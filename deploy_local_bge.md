# 部署本地 BGE Embedding 服务

## 方案一: 使用 FastAPI + sentence-transformers (推荐)

### 1. 在服务器上安装依赖

```bash
# 创建新的 conda 环境
conda create -n bge python=3.10 -y
conda activate bge

# 安装 PyTorch GPU 版本 (CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 或者使用 CUDA 12.1
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 安装其他依赖
pip install fastapi uvicorn sentence-transformers

# 验证 GPU 可用
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 2. 创建 BGE 服务脚本

保存为 `bge_server.py`:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from typing import List
import uvicorn

app = FastAPI(title="BGE Embedding Service")

# 加载模型 (首次运行会自动下载)
# 使用 BAAI/bge-large-zh-v1.5 (中文优化版本)
print("正在加载 BGE 模型...")
model = SentenceTransformer('BAAI/bge-large-zh-v1.5')
print("模型加载完成!")

class EmbeddingRequest(BaseModel):
    input: List[str]

class EmbeddingResponse(BaseModel):
    data: List[dict]
    model: str = "bge-large-zh-v1.5"

@app.post("/v1/embeddings")
async def create_embeddings(request: EmbeddingRequest):
    try:
        # 生成 embeddings
        embeddings = model.encode(
            request.input,
            normalize_embeddings=True,  # 归一化
            show_progress_bar=False
        )
        
        # 格式化响应 (兼容 OpenAI API 格式)
        data = [
            {
                "object": "embedding",
                "embedding": embedding.tolist(),
                "index": i
            }
            for i, embedding in enumerate(embeddings)
        ]
        
        return EmbeddingResponse(data=data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "model": "bge-large-zh-v1.5"}

if __name__ == "__main__":
    # 启动服务
    uvicorn.run(
        app,
        host="0.0.0.0",  # 允许外部访问
        port=8001,       # 使用 8001 端口
        workers=1        # 单进程 (模型占用显存)
    )
```

### 3. 启动服务

```bash
# 在服务器上运行
conda activate bge
nohup python bge_server.py > bge_server.log 2>&1 &
```

### 4. 测试服务

```bash
# 本地测试
curl -X POST http://localhost:8001/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input":["测试文本"]}'
```

### 5. 修改项目配置

修改 `code/backend/config/settings.py`:

```python
# BGE API URL - 改为服务器地址
self.bge_api_url: str = os.getenv(
    "BGE_API_URL",
    "http://your-server-ip:8001/v1/embeddings"  # 改为你的服务器 IP
)
```

或者在 `.env` 文件中设置:

```bash
BGE_API_URL=http://your-server-ip:8001/v1/embeddings
```

---

## 方案二: 使用 vLLM 部署 (高性能,支持批处理)

### 1. 安装 vLLM

```bash
conda create -n vllm python=3.10 -y
conda activate vllm
pip install vllm
```

### 2. 启动 vLLM 服务

```bash
python -m vllm.entrypoints.openai.api_server \
    --model BAAI/bge-large-zh-v1.5 \
    --port 8001 \
    --host 0.0.0.0
```

---

## 性能对比

| 方案 | 速度 | 显存占用 | 并发能力 | 推荐场景 |
|------|------|----------|----------|----------|
| sentence-transformers | 中等 | ~2GB | 低 | 小规模使用 |
| vLLM | 快 | ~4GB | 高 | 大规模生产 |

---

## 模型信息

- **模型**: BAAI/bge-large-zh-v1.5
- **维度**: 1024
- **语言**: 中文优化
- **大小**: ~1.3GB
- **适用**: 中文文本检索

---

## 注意事项

1. **首次运行会自动下载模型** (~1.3GB),需要网络
2. **建议使用 GPU** 加速 (没有 GPU 也能用 CPU,但较慢)
3. **如果服务器没有公网 IP**,可以用 frp/ngrok 等内网穿透
4. **生产环境建议**:
   - 使用 systemd 管理服务
   - 配置 nginx 反向代理
   - 添加访问认证

---

## 迁移步骤

1. ✅ 在服务器部署 BGE 服务
2. ✅ 修改 backend 配置指向新服务
3. ✅ 测试 embedding 生成
4. ✅ 重新运行向量数据库构建脚本
5. ✅ 重启后端服务

---

## 故障排查

### 模型下载失败
```bash
# 手动指定镜像
export HF_ENDPOINT=https://hf-mirror.com
```

### 显存不足
```python
# 使用 CPU 模式
model = SentenceTransformer('BAAI/bge-large-zh-v1.5', device='cpu')
```

### 连接超时
```python
# 增加超时时间
requests.post(url, json=data, timeout=60)
```
