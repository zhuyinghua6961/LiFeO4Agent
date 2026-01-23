# 批量处理PDF脚本

## 使用方法

### 1. 确保Marker服务已启动

```bash
# 在marker_service目录下启动服务
cd marker_service
python server.py
```

### 2. 运行批处理脚本

```bash
# 基础用法
python marker_service/batch_process_pdf/batch_process_pdfs.py \
  --pdf-dir /code/papers \
  --marker-url http://localhost:8002 \
  --max-workers 10 \
  --output-dir /code/processed_papers
```

### 参数说明

- `--pdf-dir`: PDF文件目录（默认：`/code/papers`）
- `--marker-url`: Marker服务地址（默认：`http://localhost:8002`）
- `--max-workers`: 并发请求数（默认：10）
- `--output-dir`: 输出目录（默认：`/code/processed_papers`）

### 3. 查看结果

```bash
# 输出目录结构
/code/processed_papers/
├── DOI_001/
│   └── content.md          # Markdown文件
├── DOI_002/
│   └── content.md
└── batch_processing_report.json  # 批处理报告
```

## 环境变量

可以通过环境变量配置Marker服务地址：

```bash
export MARKER_SERVICE_URL=http://gpu-server:8002
python marker_service/batch_process_pdf/batch_process_pdfs.py --pdf-dir /code/papers
```

## 性能

- 单个PDF（30页）：~2分钟
- 100篇论文（10并发）：~20分钟
- 建议并发数：5-10（取决于GPU服务器性能）

## 输出

每个PDF只生成一个文件：
- `content.md`: 干净的Markdown文本（已过滤图片乱码、页眉页脚）

批处理报告包含：
- 总数、成功数、失败数
- 成功率
- 总耗时、平均耗时
- 每个PDF的详细结果
