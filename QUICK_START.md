# 🚀 快速启动指南

## 一键启动（推荐）

```bash
# 1. 激活环境
conda activate py310

# 2. 测试构建（5-10分钟）
python build_sentence_vector_db.py --test

# 3. 检查结果
python check_sentence_db_status.py
```

## 如果测试成功，运行完整构建

```bash
# 完整构建（2-5小时）
python build_sentence_vector_db.py --full
```

## 构建完成后

```bash
# 再次检查状态
python check_sentence_db_status.py
```

## 预期输出

### 测试模式（100个DOI）
```
✅ 提取到 5847 个DOI
✅ 创建成功
✅ 处理成功: 98
✅ 提取句子数: 1847
✅ 平均每个DOI句子数: 18.8
```

### 完整模式（所有DOI）
```
✅ 提取到 5847 个DOI
✅ 创建成功
✅ 处理成功: 5700+
✅ 提取句子数: 100,000+
✅ 平均每个DOI句子数: 15-25
```

## 故障排查

### 如果出现错误

1. **检查环境**
```bash
conda activate py310
python --version  # 应该是 Python 3.10.x
```

2. **检查配置**
```bash
# 检查向量数据库路径
ls -la /Users/zhuyinghua/Desktop/code/vector_database_v3
```

3. **检查BGE API**
```bash
curl http://172.18.8.31:8001/v1/embeddings
```

4. **查看详细日志**
```bash
# 程序会自动显示详细进度和错误信息
```

## 下一步

构建完成后，参考以下文档：

- `RAG_CITATION_ARCHITECTURE.md` - 了解如何集成到RAG系统
- `SENTENCE_DB_README.md` - 完整使用文档
- `RECOMMENDED_TEST_QUESTIONS.md` - 测试引用准确性

---

**就这么简单！开始构建吧！** 🎉
