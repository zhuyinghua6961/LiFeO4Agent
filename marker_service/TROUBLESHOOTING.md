# Marker Service 故障排查指南

## 常见问题

### 1. RuntimeError: The size of tensor a (X) must match the size of tensor b (Y)

**问题描述:**
```
RuntimeError: The size of tensor a (6) must match the size of tensor b (5) at non-singleton dimension 0
```

**原因:**
- 这是 marker-pdf/surya 库内部的 bug
- 通常发生在批处理多个PDF时，不同页面的特征维度不一致
- 并发处理时模型内部缓存状态冲突

**解决方案:**

1. **降低并发数量** (已实现)
   - 修改 `conversion_lock = threading.Semaphore(1)` 改为串行处理
   - 避免模型内部状态冲突

2. **添加重试机制** (已实现)
   - 自动重试失败的转换（最多2次）
   - 每次重试前清理GPU缓存
   - 代码已添加到 `convert_pdf` 和批量转换接口

3. **临时解决方案:**
   - 如果某个PDF持续失败，尝试单独转换
   - 检查PDF是否损坏或格式特殊
   - 使用其他PDF转换工具预处理

### 2. 模型加载失败

**问题描述:**
```
ImportError: cannot import name 'load_all_models' from 'marker.models'
```

**解决方案:**
- 确保使用 marker-pdf v1.10+ 版本
- 使用新API: `create_model_dict()` 和 `PdfConverter`
- 参考 `API_MIGRATION.md` 文档

### 3. GPU内存不足

**症状:**
- CUDA out of memory 错误
- 服务崩溃或无响应

**解决方案:**
```python
# 在处理前清理缓存
import torch
if torch.cuda.is_available():
    torch.cuda.empty_cache()

# 降低并发数量
conversion_lock = threading.Semaphore(1)
```

### 4. 服务启动慢

**原因:**
- 首次启动需要下载模型文件（数GB）
- 模型加载到GPU需要时间

**解决方案:**
- 启动时预加载模型（已实现）
- 确保网络连接良好
- 使用SSD存储模型文件

## 日志分析

### 正常运行日志:
```
✅ 模型加载成功！耗时: 3.4秒
🎉 服务启动成功！
📄 开始处理PDF: example.pdf
✅ PDF处理成功: example.pdf, 耗时: 5.3秒
```

### 错误日志:
```
❌ PDF处理失败: example.pdf, 错误: ...
⚠️ 转换失败 (尝试 1/2): ...
🔄 清理缓存后重试...
```

## 性能优化建议

1. **使用更强的GPU** - RTX 3090 或更高
2. **串行处理** - 避免并发冲突（当前配置）
3. **增加内存** - 至少16GB RAM + 12GB VRAM
4. **使用生产级WSGI服务器** - gunicorn 或 uwsgi

## 报告问题

如果问题持续存在，请提供：
1. 完整的错误日志
2. PDF文件信息（页数、大小、来源）
3. GPU型号和内存
4. marker-pdf 版本: `pip show marker-pdf`
