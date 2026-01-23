# Marker API 迁移说明

## 变更概述

`marker_service` 已从旧版 marker API 迁移到新版 marker-pdf v1.10+ API。

## 主要变更

### 1. 模型加载

**旧API (已弃用):**
```python
from marker.convert import convert_single_pdf
from marker.models import load_all_models

model_lst = load_all_models()
```

**新API (v1.10+):**
```python
from marker.models import create_model_dict
from marker.converters.pdf import PdfConverter

# 创建模型字典
model_dict = create_model_dict()

# 创建转换器 (renderer参数使用字符串类名)
converter = PdfConverter(
    artifact_dict=model_dict,
    renderer="marker.renderers.markdown.MarkdownRenderer"
)
```

### 2. PDF转换

**旧API:**
```python
full_text, images, out_meta = convert_single_pdf(
    pdf_path,
    model_lst=model_lst,
    langs=['en', 'zh'],
    batch_multiplier=2,
    max_pages=None
)
```

**新API:**
```python
# 转换器是可调用对象
rendered = converter(pdf_path)

# 提取markdown文本
markdown_text = rendered.markdown
```

### 3. 返回值变化

- **旧API**: 返回 `(full_text, images, metadata)` 元组
- **新API**: 返回渲染对象，通过 `.markdown` 属性访问文本

## 迁移后的改进

1. ✅ **API兼容性**: 使用最新的 marker-pdf 包
2. ✅ **模型预加载**: 启动时或首次请求时加载（单例模式）
3. ✅ **并发控制**: 使用信号量限制并发转换数量
4. ✅ **错误处理**: 改进的异常处理和日志记录
5. ✅ **批量转换**: 支持多文件批量处理

## 测试

运行以下命令测试新API：

```bash
# 测试API导入和结构
conda run -n marker python test_new_api.py

# 测试服务导入
conda run -n marker python -c "import server; print('✅ OK')"

# 启动服务
conda run -n marker python server.py
```

## 注意事项

1. 新API不再支持 `langs`, `batch_multiplier`, `max_pages` 参数
2. 模型加载可能需要首次下载模型文件（需要网络连接）
3. 建议在启动时预加载模型以获得最佳性能

## 相关文件

- `server.py` - 主服务文件（已更新）
- `test_new_api.py` - API测试脚本
- `README.md` - 服务文档（已更新）
