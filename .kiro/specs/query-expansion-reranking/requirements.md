# Requirements Document

## Introduction

本需求文档描述了检索系统的查询扩展和重排序功能改进。当前系统存在一级检索（段落级）召回率不足的问题，导致某些精确问题（如"磷酸铁锂的压实密度是多少？"）无法找到相关文献。本改进通过多查询策略和句子级重排序来提升检索质量。

## Glossary

- **一级检索 (Primary Retrieval)**: 基于段落级向量数据库的初始检索
- **二级检索 (Secondary Retrieval)**: 基于句子级向量数据库的精确匹配
- **查询扩展 (Query Expansion)**: 将单一查询扩展为多个相关查询（中文、英文、同义词）
- **重排序 (Reranking)**: 使用句子级相似度对检索结果重新排序
- **召回率 (Recall)**: 检索到的相关文献占所有相关文献的比例
- **精确度 (Precision)**: 检索到的相关文献占所有检索结果的比例
- **BGE API**: 用于生成文本embedding的API服务
- **SemanticExpert**: 语义搜索专家类，负责文献检索
- **VectorRepository**: 向量数据库仓储类

## Requirements

### Requirement 1

**User Story:** 作为系统用户，我希望系统能够通过多语言查询找到相关文献，以便提高检索的召回率。

#### Acceptance Criteria

1. WHEN 用户提交中文查询 THEN SemanticExpert SHALL 生成对应的英文查询
2. WHEN 用户提交查询 THEN SemanticExpert SHALL 生成包含同义词的扩展查询
3. WHEN 生成多个查询 THEN SemanticExpert SHALL 对每个查询执行向量检索
4. WHEN 多个查询返回结果 THEN SemanticExpert SHALL 合并结果并去除重复的DOI
5. WHERE 查询扩展功能启用 THEN 扩展查询数量 SHALL 不超过3个

### Requirement 2

**User Story:** 作为系统用户，我希望检索结果按照句子级相似度重新排序，以便最相关的文献排在前面。

#### Acceptance Criteria

1. WHEN 一级检索返回候选文献 THEN SemanticExpert SHALL 使用句子级数据库计算每个文献的最高相似度
2. WHEN 计算句子级相似度 THEN SemanticExpert SHALL 在句子数据库中查询每个候选DOI的所有句子
3. WHEN 获取候选文献的句子 THEN SemanticExpert SHALL 计算查询与每个句子的相似度
4. WHEN 计算完所有相似度 THEN SemanticExpert SHALL 按最高相似度降序排列文献
5. WHEN 重排序完成 THEN SemanticExpert SHALL 返回top-k个文献

### Requirement 3

**User Story:** 作为系统开发者，我希望查询扩展功能可配置，以便根据不同场景调整策略。

#### Acceptance Criteria

1. WHEN 初始化SemanticExpert THEN 系统 SHALL 从配置文件读取查询扩展开关
2. WHERE 查询扩展开关关闭 THEN SemanticExpert SHALL 使用原有的单查询策略
3. WHERE 查询扩展开关开启 THEN SemanticExpert SHALL 使用多查询策略
4. WHEN 配置文件不存在 THEN SemanticExpert SHALL 使用默认配置（开启查询扩展）
5. WHEN 查询扩展失败 THEN SemanticExpert SHALL 回退到单查询策略

### Requirement 4

**User Story:** 作为系统用户，我希望系统能够智能翻译中文查询为英文，以便匹配英文文献。

#### Acceptance Criteria

1. WHEN 检测到查询包含中文 THEN SemanticExpert SHALL 调用翻译服务生成英文查询
2. WHEN 翻译服务不可用 THEN SemanticExpert SHALL 使用预定义的中英文术语映射表
3. WHEN 使用术语映射表 THEN SemanticExpert SHALL 替换查询中的关键术语
4. WHEN 翻译完成 THEN 英文查询 SHALL 保留原始查询的核心语义
5. IF 翻译失败 THEN SemanticExpert SHALL 记录警告并继续使用中文查询

### Requirement 5

**User Story:** 作为系统用户，我希望系统能够生成同义词查询，以便覆盖不同的表达方式。

#### Acceptance Criteria

1. WHEN 提取查询关键词 THEN SemanticExpert SHALL 识别关键术语
2. WHEN 识别到关键术语 THEN SemanticExpert SHALL 从同义词库中查找同义词
3. WHEN 找到同义词 THEN SemanticExpert SHALL 生成包含同义词的新查询
4. WHEN 生成同义词查询 THEN 新查询 SHALL 保持原查询的主要概念
5. WHERE 同义词库不存在 THEN SemanticExpert SHALL 使用预定义的常见同义词列表

### Requirement 6

**User Story:** 作为系统开发者，我希望重排序功能能够高效处理大量候选文献，以便保持系统响应速度。

#### Acceptance Criteria

1. WHEN 候选文献数量超过20篇 THEN SemanticExpert SHALL 只对前20篇进行重排序
2. WHEN 查询句子数据库 THEN SemanticExpert SHALL 使用批量查询减少API调用次数
3. WHEN 计算相似度 THEN SemanticExpert SHALL 使用向量化操作提高计算效率
4. WHEN 重排序耗时超过5秒 THEN SemanticExpert SHALL 记录性能警告
5. WHEN 重排序失败 THEN SemanticExpert SHALL 返回原始排序结果

### Requirement 7

**User Story:** 作为系统用户，我希望看到查询扩展和重排序的详细日志，以便理解检索过程。

#### Acceptance Criteria

1. WHEN 执行查询扩展 THEN SemanticExpert SHALL 记录所有生成的查询
2. WHEN 执行多查询检索 THEN SemanticExpert SHALL 记录每个查询的结果数量
3. WHEN 合并结果 THEN SemanticExpert SHALL 记录去重前后的文献数量
4. WHEN 执行重排序 THEN SemanticExpert SHALL 记录重排序前后的top-3文献
5. WHEN 检索完成 THEN SemanticExpert SHALL 记录总耗时和各阶段耗时

### Requirement 8

**User Story:** 作为系统测试人员，我希望能够验证查询扩展和重排序功能的正确性，以便确保改进有效。

#### Acceptance Criteria

1. WHEN 测试"压实密度"查询 THEN 系统 SHALL 返回包含相关DOI的结果
2. WHEN 对比改进前后 THEN 召回率 SHALL 提升至少20%
3. WHEN 对比改进前后 THEN 精确度 SHALL 保持或提升
4. WHEN 测试多个查询 THEN 平均响应时间 SHALL 不超过10秒
5. WHEN 测试边界情况 THEN 系统 SHALL 正确处理空查询、超长查询等异常输入
