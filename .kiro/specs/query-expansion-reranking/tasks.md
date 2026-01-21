# Implementation Plan

- [x] 1. 创建配置文件和核心术语表（方案C：混合方式）
  - 在 `backend/config/settings.py` 中添加查询扩展配置项
  - 创建核心术语映射表 `backend/config/term_mapping.json`（10-15个常用术语）
  - 创建核心同义词库 `backend/config/synonyms.json`（5-10组同义词）
  - 主要依赖LLM，术语表作为回退和补充
  - 添加日志记录功能，记录查询失败案例以便后续扩展
  - _Requirements: 3.1, 3.4_
  - _核心术语基于：磷酸铁锂领域常见术语、已测试的问题（压实密度、导电率等）_

- [x] 2. 实现 QueryExpander 类
  - 创建 `backend/agents/query_expander.py` 文件
  - 实现 `__init__()` 方法，加载配置和数据文件
  - 实现 `translate_to_english()` 方法（LLM翻译 + 术语映射表回退）
  - 实现 `generate_synonyms()` 方法（同义词库查询）
  - 实现 `expand()` 方法（整合翻译和同义词）
  - _Requirements: 1.1, 1.2, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_

- [x] 2.1 为 QueryExpander 编写单元测试
  - 测试中英文翻译功能
  - 测试同义词生成功能
  - 测试查询扩展功能
  - 测试回退逻辑
  - _Requirements: 1.1, 1.2, 4.1, 5.1_

- [x] 2.2 编写查询扩展的属性测试
  - **Property 1: Query expansion preserves original**
  - **Validates: Requirements 1.4**

- [x] 3. 实现 MultiQueryRetriever 类
  - 记住使用 conda 环境 py310
  - 创建 `backend/agents/multi_query_retriever.py` 文件
  - 实现 `__init__()` 方法
  - 实现 `_generate_embeddings_batch()` 方法（批量生成embedding）
  - 实现 `_retrieve_single()` 方法（单个查询检索）
  - 实现 `deduplicate_by_doi()` 方法（按DOI去重，保留最高相似度）
  - 实现 `retrieve()` 方法（多查询检索主方法）
  - _Requirements: 1.3, 1.4, 1.5_

- [x] 3.1 为 MultiQueryRetriever 编写单元测试
  - 测试批量embedding生成
  - 测试去重逻辑
  - 测试多查询合并
  - _Requirements: 1.3, 1.4_

- [x] 3.2 编写去重的属性测试
  - **Property 2: Deduplication is idempotent**
  - **Validates: Requirements 1.4**

- [x] 3.3 编写DOI提取的属性测试
  - **Property 10: DOI extraction completeness**
  - **Validates: Requirements 1.4**

- [x] 4. 实现 SentenceReranker 类
  - 创建 `backend/agents/sentence_reranker.py` 文件
  - 实现 `__init__()` 方法
  - 实现 `_compute_max_sentence_similarity()` 方法（计算DOI的最高句子相似度）
  - 实现 `_batch_query_sentences()` 方法（批量查询句子数据库）
  - 实现 `rerank()` 方法（重排序主方法）
  - 添加结果缓存（使用 `lru_cache`）
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 6.1, 6.2, 6.3_

- [x] 4.1 为 SentenceReranker 编写单元测试
  - 测试相似度计算
  - 测试排序逻辑
  - 测试缓存功能
  - _Requirements: 2.1, 2.3, 2.4_

- [x] 4.2 编写重排序的属性测试
  - **Property 3: Reranking preserves all candidates**
  - **Validates: Requirements 2.4**

- [x] 4.3 编写相似度的属性测试
  - **Property 4: Sentence similarity is bounded**
  - **Validates: Requirements 2.3**

- [x] 4.4 编写重排序改进的属性测试
  - **Property 7: Reranking improves relevance ordering**
  - **Validates: Requirements 2.4**

- [x] 5. 集成到 SemanticExpert
  - 在 `SemanticExpert.__init__()` 中初始化三个新组件
  - 实现 `search_with_expansion()` 方法
  - 添加详细日志记录（每个步骤的耗时和结果）
  - 实现错误处理和回退逻辑
  - _Requirements: 3.2, 3.3, 3.5, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 5.1 编写回退逻辑的属性测试
  - **Property 8: Fallback preserves functionality**
  - **Validates: Requirements 3.5, 6.5**

- [x] 6. 更新 query_with_details() 方法
  - 修改 `query_with_details()` 使用新的 `search_with_expansion()` 方法
  - 添加配置开关判断（enable_query_expansion）
  - 保持向后兼容性
  - _Requirements: 3.2, 3.3_

- [x] 7. Checkpoint - 确保所有测试通过
  - 运行所有单元测试
  - 运行所有属性测试
  - 修复发现的问题
  - 确保所有测试通过，询问用户是否有问题

- [x] 8. 创建端到端测试脚本
  - 创建 `test_query_expansion_e2e.py` 测试脚本
  - 测试"压实密度"问题（已知失败案例）
  - 测试"导电率"问题（对比改进前后）
  - 测试"循环性能"问题（宽泛问题）
  - 记录召回率和精确度指标
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 8.1 编写性能测试
  - 测试响应时间<10秒
  - 测试批量查询性能
  - 测试重排序性能
  - _Requirements: 6.4, 8.4_

- [x] 8.2 编写边界情况测试
  - 测试空查询
  - 测试超长查询
  - 测试特殊字符
  - _Requirements: 8.5_

- [x] 9. 性能优化
  - 添加并行查询（ThreadPoolExecutor）
  - 优化批量API调用
  - 添加结果缓存
  - 限制重排序候选数量（top-20）
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 10. 文档和日志完善
  - 添加详细的docstring
  - 完善日志输出（包含耗时统计）
  - 创建使用示例文档
  - 更新 README
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 11. Final Checkpoint - 验证改进效果
  - 运行完整的端到端测试
  - 对比改进前后的召回率（目标+20%）
  - 对比改进前后的精确度（目标保持或提升）
  - 验证"压实密度"问题已解决
  - 确保所有测试通过，询问用户是否满意
