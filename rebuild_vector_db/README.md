# Rebuild Vector Database

重建科学论文向量数据库的工具模块。

## 文档管理规则

⚠️ **重要约束**：
- 每个模块最多只允许创建一个 README.md
- 严禁创建其他文档（SETUP.md, INFO.md, SUMMARY.md 等）
- 所有测试代码在测试通过后必须立即删除
- 临时验证脚本在验证完成后必须删除

## 目录结构

```
rebuild_vector_db/
├── __init__.py              # 包初始化
├── chunk_splitter.py        # Chunk 切分模块
├── sentence_splitter.py     # 句子切分模块
├── bge_embedder.py          # BGE 向量化模块
├── chromadb_manager.py      # ChromaDB 管理模块
├── pipeline.py              # 重建流程协调模块
├── requirements.txt         # Python 依赖
└── validate_setup.py        # 设置验证脚本（开发完成后删除）
```

## 配置

配置文件：`config/rebuild_config.yaml`

BGE API 服务：`http://localhost:8001/v1/embeddings` (已启动)

## 环境

所有代码必须在 `agent` conda 环境下运行：

```bash
conda run -n agent python <script.py>
```

## 验证设置

```bash
PYTHONPATH=. conda run -n agent python rebuild_vector_db/validate_setup.py
```
