# query_with_details() 方法更新文档

## 概述

`query_with_details()` 方法已更新，支持根据配置自动选择使用查询扩展和重排序策略，或使用原有的单查询策略。

## 更新内容

### 1. 配置开关

方法现在会检查以下配置项：
- `settings.enable_query_expansion`: 是否启用查询扩展
- `settings.enable_reranking`: 是否启用重排序

### 2. 策略选择逻辑

```python
use_expansion = settings.enable_query_expansion or settings.enable_reranking

if use_expansion:
    # 使用新的查询扩展和重排序策略
    search_result = self.search_with_expansion(...)
else:
    # 使用原有的单查询策略（向后兼容）
    search_result = self.search(...)
```

### 3. 返回结果增强

当使用查询扩展策略时，返回的 `pdf_info` 字典会包含额外的信息：

```python
{
    'documents_found': int,          # 找到的文档数量
    'is_broad_question': bool,       # 是否为宽泛问题
    'dois_found': int,               # 找到的DOI数量
    'pdf_loaded': int,               # 成功加载的PDF数量
    'pdf_failed': int,               # 加载失败的PDF数量
    'used_expansion': bool,          # 是否使用了查询扩展
    'expansion_info': dict,          # 查询扩展信息
    'retrieval_info': dict,          # 检索信息
    'reranking_info': dict,          # 重排序信息
    'timing': dict                   # 耗时信息
}
```

## 向后兼容性

- 当配置禁用查询扩展和重排序时，方法行为与之前完全一致
- 返回结果格式保持兼容，只是添加了额外的可选字段
- 现有代码无需修改即可继续使用

## 使用示例

### 示例 1: 启用查询扩展和重排序

```python
# 在 config.env 中设置
ENABLE_QUERY_EXPANSION=True
ENABLE_RERANKING=True

# 使用
expert = SemanticExpert(vector_repo, llm_service)
result = expert.query_with_details("磷酸铁锂的压实密度是多少？")

# 结果包含扩展信息
print(result['pdf_info']['used_expansion'])  # True
print(result['pdf_info']['expansion_info'])  # 查询扩展详情
print(result['pdf_info']['timing'])          # 各阶段耗时
```

### 示例 2: 禁用查询扩展（向后兼容）

```python
# 在 config.env 中设置
ENABLE_QUERY_EXPANSION=False
ENABLE_RERANKING=False

# 使用
expert = SemanticExpert(vector_repo, llm_service)
result = expert.query_with_details("磷酸铁锂的压实密度是多少？")

# 使用原有的单查询策略
print(result['pdf_info']['used_expansion'])  # False
```

## 配置说明

在 `backend/config.env` 文件中添加以下配置：

```bash
# 查询扩展配置
ENABLE_QUERY_EXPANSION=True    # 是否启用查询扩展
ENABLE_RERANKING=True          # 是否启用重排序
MAX_QUERIES=3                  # 最大查询数量

# 重排序配置
RERANK_TOP_K=20               # 只对前20个候选重排序
RERANK_TIMEOUT=5              # 重排序超时（秒）
```

## 实现细节

### Requirements 验证

✅ **Requirement 3.2**: 配置开关关闭时使用原有的单查询策略
- 实现：通过 `use_expansion` 变量判断，当为 False 时调用 `self.search()`

✅ **Requirement 3.3**: 配置开关开启时使用多查询策略
- 实现：当 `use_expansion` 为 True 时调用 `self.search_with_expansion()`

### 错误处理

方法保持了原有的错误处理逻辑：
- 检索失败时返回错误信息
- 空结果时返回友好提示
- 所有错误情况都有适当的日志记录

### 日志输出

方法会记录使用的策略：
```
🚀 使用查询扩展和重排序策略
```
或
```
📚 使用原有的单查询策略
```

## 测试建议

### 手动测试

1. **测试查询扩展启用**:
   ```python
   # 设置 ENABLE_QUERY_EXPANSION=True
   result = expert.query_with_details("压实密度")
   assert result['pdf_info']['used_expansion'] == True
   ```

2. **测试查询扩展禁用**:
   ```python
   # 设置 ENABLE_QUERY_EXPANSION=False
   result = expert.query_with_details("压实密度")
   assert result['pdf_info']['used_expansion'] == False
   ```

3. **测试向后兼容性**:
   ```python
   # 禁用扩展，验证返回格式
   result = expert.query_with_details("压实密度")
   assert 'answer' in result
   assert 'pdf_info' in result
   assert 'doi_locations' in result
   ```

## 相关文件

- 实现文件: `backend/agents/experts/semantic_expert.py`
- 配置文件: `backend/config/settings.py`
- 环境配置: `backend/config.env`
- 设计文档: `.kiro/specs/query-expansion-reranking/design.md`
- 需求文档: `.kiro/specs/query-expansion-reranking/requirements.md`

## 总结

此更新实现了以下目标：
1. ✅ 添加配置开关判断（enable_query_expansion）
2. ✅ 修改 query_with_details() 使用新的 search_with_expansion() 方法
3. ✅ 保持向后兼容性
4. ✅ 满足 Requirements 3.2 和 3.3
