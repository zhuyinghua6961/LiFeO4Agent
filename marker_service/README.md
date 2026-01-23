# Marker PDF转换服务

将PDF文档转换为Markdown格式的HTTP服务。

## 功能特点

- ✅ PDF → Markdown转换
- ✅ 支持中英文双语
- ✅ GPU加速处理
- ✅ 支持单个和批量转换
- ✅ RESTful API接口
- ✅ 健康检查接口
- ✅ 并发请求支持

## 快速开始

### 1. 安装依赖

```bash
# 创建conda环境
conda create -n marker python=3.10 -y
conda activate marker

# 安装PyTorch (CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 安装其他依赖
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 方式1: 使用启动脚本
chmod +x start.sh
./start.sh

# 方式2: 直接运行
python server.py
```

服务将在 `http://0.0.0.0:8002` 启动。

### 3. 测试服务

```bash
# 健康检查
curl http://localhost:8002/health

# 转换单个PDF
python test_client.py /path/to/your.pdf

# 批量转换
python test_client.py /path/to/pdf1.pdf /path/to/pdf2.pdf
```

## API接口

### 1. 健康检查

```bash
GET /health
```

响应:
```json
{
  "status": "healthy",
  "service": "marker-pdf-service",
  "model_loaded": true,
  "model_load_time": "2025-01-23T10:30:00",
  "timestamp": "2025-01-23T11:00:00"
}
```

### 2. 转换单个PDF

```bash
POST /api/convert_pdf
```

参数:
- `file`: PDF文件（必需）
- `langs`: 语言列表，逗号分隔（可选，默认"en,zh"）
- `batch_multiplier`: 批处理倍数（可选，默认2）
- `max_pages`: 最大处理页数（可选，默认None=全部）

示例:
```bash
curl -X POST http://localhost:8002/api/convert_pdf \
  -F "file=@paper.pdf" \
  -F "langs=en,zh"
```

响应:
```json
{
  "success": true,
  "markdown": "# Paper Title\n\n...",
  "metadata": {
    "pages": 30,
    "processing_time": 95.3,
    "filename": "paper.pdf"
  }
}
```

### 3. 批量转换PDF

```bash
POST /api/batch_convert
```

参数:
- `files`: 多个PDF文件（必需）
- `langs`: 语言列表（可选）

示例:
```bash
curl -X POST http://localhost:8002/api/batch_convert \
  -F "files=@paper1.pdf" \
  -F "files=@paper2.pdf" \
  -F "langs=en,zh"
```

响应:
```json
{
  "success": true,
  "total": 2,
  "succeeded": 2,
  "failed": 0,
  "results": [
    {
      "filename": "paper1.pdf",
      "success": true,
      "markdown": "...",
      "metadata": {...}
    },
    {
      "filename": "paper2.pdf",
      "success": true,
      "markdown": "...",
      "metadata": {...}
    }
  ]
}
```

## Python客户端示例

```python
import requests

# 服务地址
MARKER_SERVICE_URL = "http://localhost:8002"

# 转换PDF
with open('paper.pdf', 'rb') as f:
    files = {'file': f}
    data = {'langs': 'en,zh'}
    
    response = requests.post(
        f"{MARKER_SERVICE_URL}/api/convert_pdf",
        files=files,
        data=data,
        timeout=300
    )
    
    if response.ok:
        result = response.json()
        if result['success']:
            markdown = result['markdown']
            print(f"转换成功！文本长度: {len(markdown)}")
        else:
            print(f"转换失败: {result['error']}")
```

## 性能

- **单个PDF**: 2-3分钟（30页论文）
- **并发处理**: 支持多个并发请求
- **显存占用**: ~8-10GB（24GB显存可同时处理2-3个请求）

## 部署建议

### 使用systemd（推荐）

创建服务文件 `/etc/systemd/system/marker.service`:

```ini
[Unit]
Description=Marker PDF Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/marker_service
Environment="PATH=/home/your_user/miniconda3/envs/marker/bin"
ExecStart=/home/your_user/miniconda3/envs/marker/bin/python server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl daemon-reload
sudo systemctl start marker
sudo systemctl enable marker  # 开机自启
sudo systemctl status marker  # 查看状态
```

### 使用Docker

```dockerfile
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3.10 python3-pip

WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY server.py .

EXPOSE 8002

CMD ["python3", "server.py"]
```

构建和运行:
```bash
docker build -t marker-service .
docker run --gpus all -p 8002:8002 marker-service
```

## 故障排查

### 1. 模型加载失败

检查GPU是否可用:
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

### 2. 端口被占用

更改端口（修改server.py最后一行）:
```python
app.run(host='0.0.0.0', port=8003)  # 改为其他端口
```

### 3. 内存不足

减少batch_multiplier:
```python
# 在请求中设置
data = {'batch_multiplier': 1}  # 从2降到1
```

## 日志

服务日志会输出到控制台，包含:
- 模型加载状态
- 每个请求的处理时间
- 错误信息

查看systemd服务日志:
```bash
sudo journalctl -u marker -f
```

## 许可证

MIT License
