# Design Document: Query Expansion and Reranking

## Overview

本设计文档描述了检索系统的查询扩展和重排序功能。该功能通过多查询策略提升召回率，通过句子级重排序提升精确度，解决当前一级检索（段落级）召回率不足的问题。

**核心改进**:
1. **查询扩展**: 将单一查询扩展为多个查询（中文、英文、同义词）
2. **多查询检索**: 并行执行多个查询并合并结果
3. **句子级重排序**: 使用句子数据库计算精确相似度并重新排序
4. **智能回退**: 查询扩展失败时回退到单查询策略

**预期效果**:
- 召回率提升 +30%
- 精确度提升 +20%
- 引用成功率提升 +40%

## Architecture

### 系统架构图

```
用户问题
    ↓
┌─────────────────────────────────────────┐
│  SemanticExpert.search_with_expansion() │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  1. 查询扩展 (Query Expansion)           │
│     - 中文→英文翻译                      │
│     - 同义词扩展                         │
│     - 生成3个查询                        │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  2. 多查询检索 (Multi-Query Retrieval)   │
│     - 并行执行3个查询                    │
│     - 每个查询返回top-20                 │
│     - 合并结果（去重）                   │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  3. 句子级重排序 (Sentence-Level Rerank) │
│     - 在句子数据库中查询每个候选DOI      │
│     - 计算最高句子相似度                 │
│     - 按相似度降序排列                   │
└─────────────────────────────────────────┘
    ↓
返回 top-15 文献
```

### 数据流

```
输入: "磷酸铁锂的压实密度是多少？"
    ↓
查询扩展:
    - Query 1: "磷酸铁锂 压实密度" (原始)
    - Query 2: "LiFePO4 compaction density" (英文)
    - Query 3: "磷酸铁锂 电极密度 压制" (同义词)
    ↓
多查询检索:
    - Query 1 → 20个段落 (10个DOI)
    - Query 2 → 20个段落 (12个DOI)
    - Query 3 → 20个段落 (8个DOI)
    - 合并去重 → 30个段落 (22个DOI)
    ↓
句子级重排序:
    - DOI_1: 最高句子相似度 = 0.72
    - DOI_2: 最高句子相似度 = 0.68
    - DOI_3: 最高句子相似度 = 0.65
    - ...
    - 按相似度排序
    ↓
输出: top-15 文献（相关文献排在前面）
```

## Components and Interfaces

### 1. QueryExpander (查询扩展器)

**职责**: 将单一查询扩展为多个查询

**接口**:
```python
class QueryExpander:
    def __init__(self, llm_service: Optional[LLMService] = None):
        """初始化查询扩展器"""
        pass
    
    def expand(self, query: str) -> List[str]:
        """
        扩展查询
        
        Args:
            query: 原始查询
            
        Returns:
            扩展后的查询列表（包含原始查询）
        """
        pass
    
    def translate_to_english(self, query: str) -> str:
        """翻译为英文"""
        pass
    
    def generate_synonyms(self, query: str) -> str:
        """生成同义词查询"""
        pass
```

**实现细节**:
- 使用LLM进行中英文翻译
- 维护术语映射表（中英文对照）
- 维护同义词库（常见术语的同义词）
- 回退策略：LLM失败时使用规则

### 2. MultiQueryRetriever (多查询检索器)

**职责**: 执行多个查询并合并结果

**接口**:
```python
class MultiQueryRetriever:
    def __init__(self, vector_repo: VectorRepository, bge_api_url: str):
        """初始化多查询检索器"""
        pass
    
    def retrieve(
        self, 
        queries: List[str], 
        top_k_per_query: int = 20
    ) -> List[Dict]:
        """
        执行多查询检索
        
        Args:
            queries: 查询列表
            top_k_per_query: 每个查询返回的结果数
            
        Returns:
            合并去重后的文档列表
        """
        pass
    
    def deduplicate_by_doi(self, documents: List[Dict]) -> List[Dict]:
        """按DOI去重"""
        pass
```

**实现细节**:
- 批量生成查询embedding（减少API调用）
- 并行执行多个查询（提高效率）
- 按DOI去重（保留相似度最高的）
- 记录每个查询的贡献度

### 3. SentenceReranker (句子级重排序器)

**职责**: 使用句子数据库重新排序候选文献

**接口**:
```python
class SentenceReranker:
    def __init__(
        self, 
        sentence_collection,
        bge_api_url: str
    ):
        """初始化重排序器"""
        pass
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = 15
    ) -> List[Dict]:
        """
        重新排序候选文献
        
        Args:
            query: 原始查询
            candidates: 候选文献列表
            top_k: 返回的文献数量
            
        Returns:
            重排序后的文献列表
        """
        pass
    
    def compute_max_sentence_similarity(
        self,
        query_embedding: List[float],
        doi: str
    ) -> float:
        """计算DOI的最高句子相似度"""
        pass
```

**实现细节**:
- 生成查询embedding
- 批量查询句子数据库（按DOI过滤）
- 计算每个DOI的最高句子相似度
- 按相似度降序排列
- 缓存结果（避免重复计算）

### 4. SemanticExpert (语义搜索专家 - 主类)

**新增方法**:
```python
class SemanticExpert:
    def search_with_expansion(
        self,
        question: str,
        top_k: int = 15,
        enable_expansion: bool = True,
        enable_reranking: bool = True
    ) -> Dict[str, Any]:
        """
        使用查询扩展和重排序的检索
        
        Args:
            question: 用户问题
            top_k: 返回结果数量
            enable_expansion: 是否启用查询扩展
            enable_reranking: 是否启用重排序
            
        Returns:
            检索结果
        """
        pass
```

**集成方式**:
- 保留原有的 `search()` 方法（向后兼容）
- 新增 `search_with_expansion()` 方法
- 通过配置开关控制是否使用新功能
- 失败时自动回退到原有方法

## Data Models

### QueryExpansionResult (查询扩展结果)

```python
@dataclass
class QueryExpansionResult:
    """查询扩展结果"""
    original_query: str          # 原始查询
    english_query: str           # 英文查询
    synonym_query: str           # 同义词查询
    all_queries: List[str]       # 所有查询（去重）
    expansion_time: float        # 扩展耗时（秒）
    translation_method: str      # 翻译方法（llm/rule）
```

### MultiQueryResult (多查询检索结果)

```python
@dataclass
class MultiQueryResult:
    """多查询检索结果"""
    documents: List[Dict]        # 合并后的文档列表
    query_contributions: Dict[str, int]  # 每个查询的贡献度
    total_before_dedup: int      # 去重前的总数
    total_after_dedup: int       # 去重后的总数
    retrieval_time: float        # 检索耗时（秒）
```

### RerankingResult (重排序结果)

```python
@dataclass
class RerankingResult:
    """重排序结果"""
    documents: List[Dict]        # 重排序后的文档列表
    similarity_scores: Dict[str, float]  # 每个DOI的相似度
    reranking_time: float        # 重排序耗时（秒）
    top_3_changes: List[Tuple[str, int, int]]  # top-3的排名变化
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Query expansion preserves original query

*For any* user query, the expanded query list should always include the original query as the first element.

**Validates: Requirements 1.4**

**Rationale**: 确保即使扩展失败，也能使用原始查询进行检索。

### Property 2: Multi-query deduplication is idempotent

*For any* set of documents, applying deduplication twice should produce the same result as applying it once.

**Validates: Requirements 1.4**

**Rationale**: 去重操作应该是幂等的，多次去重不应改变结果。

### Property 3: Reranking preserves all candidates

*For any* candidate list, reranking should return the same number of documents (or fewer if top_k is specified), but never more.

**Validates: Requirements 2.4**

**Rationale**: 重排序只改变顺序，不应增加或丢失文档。

### Property 4: Sentence similarity is bounded

*For any* query and sentence, the computed similarity score should be in the range [0, 1].

**Validates: Requirements 2.3**

**Rationale**: 相似度应该是归一化的，便于比较和阈值判断。

### Property 5: Translation round-trip consistency

*For any* Chinese query, translating to English and back to Chinese should preserve the core semantic meaning.

**Validates: Requirements 4.4**

**Rationale**: 翻译应该保持语义一致性，避免信息丢失。

### Property 6: Synonym expansion increases coverage

*For any* query with synonyms, the expanded query should match at least as many documents as the original query.

**Validates: Requirements 5.3**

**Rationale**: 同义词扩展应该提高召回率，不应降低。

### Property 7: Reranking improves relevance ordering

*For any* candidate list, the top-k documents after reranking should have higher average sentence-level similarity than before reranking.

**Validates: Requirements 2.4**

**Rationale**: 重排序的目的是提高相关性，top-k的平均相似度应该提升。

### Property 8: Fallback preserves functionality

*For any* query, if expansion or reranking fails, the system should fall back to the original search method and still return valid results.

**Validates: Requirements 3.5, 6.5**

**Rationale**: 系统应该具有容错性，失败时能够降级运行。

### Property 9: Batch embedding generation consistency

*For any* list of texts, generating embeddings in batch should produce the same results as generating them individually.

**Validates: Requirements 6.2**

**Rationale**: 批量生成embedding是优化手段，不应改变结果。

### Property 10: DOI extraction completeness

*For any* document with metadata, if a DOI field exists (either 'doi' or 'DOI'), it should be extracted into the candidate pool.

**Validates: Requirements 1.4**

**Rationale**: 候选DOI池应该包含所有可用的DOI，不应遗漏。

## Error Handling

### 1. 查询扩展失败

**场景**: LLM翻译失败、同义词库不可用

**处理**:
```python
try:
    expanded_queries = query_expander.expand(query)
except Exception as e:
    logger.warning(f"查询扩展失败: {e}，回退到单查询")
    expanded_queries = [query]  # 只使用原始查询
```

### 2. 多查询检索部分失败

**场景**: 某个查询的embedding生成失败

**处理**:
```python
successful_queries = []
for query in queries:
    try:
        results = retrieve_single(query)
        successful_queries.append(results)
    except Exception as e:
        logger.warning(f"查询失败: {query}, 错误: {e}")
        continue  # 跳过失败的查询

if not successful_queries:
    raise Exception("所有查询都失败")
```

### 3. 重排序失败

**场景**: 句子数据库不可用、相似度计算失败

**处理**:
```python
try:
    reranked = sentence_reranker.rerank(query, candidates)
except Exception as e:
    logger.warning(f"重排序失败: {e}，使用原始排序")
    reranked = candidates  # 返回原始排序
```

### 4. 超时处理

**场景**: 重排序耗时过长

**处理**:
```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("重排序超时")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)  # 5秒超时

try:
    reranked = sentence_reranker.rerank(query, candidates)
finally:
    signal.alarm(0)  # 取消超时
```

### 5. 空结果处理

**场景**: 所有查询都没有返回结果

**处理**:
```python
if not documents:
    logger.warning("所有查询都没有返回结果")
    return {
        "success": True,
        "documents": [],
        "message": "未找到相关文献，请尝试其他关键词"
    }
```

## Testing Strategy

### Unit Tests

**测试范围**:
1. QueryExpander 的各个方法
   - 中英文翻译
   - 同义词生成
   - 查询扩展
   
2. MultiQueryRetriever 的去重逻辑
   - 按DOI去重
   - 保留最高相似度
   
3. SentenceReranker 的相似度计算
   - 最高句子相似度
   - 排序逻辑

**测试用例**:
```python
def test_query_expansion():
    """测试查询扩展"""
    expander = QueryExpander()
    result = expander.expand("磷酸铁锂 压实密度")
    
    assert len(result.all_queries) >= 1
    assert result.original_query == "磷酸铁锂 压实密度"
    assert "LiFePO4" in result.english_query.lower()

def test_deduplication():
    """测试去重逻辑"""
    docs = [
        {"metadata": {"doi": "10.1021/abc"}, "score": 0.8},
        {"metadata": {"doi": "10.1021/abc"}, "score": 0.7},
        {"metadata": {"doi": "10.1021/xyz"}, "score": 0.9}
    ]
    
    retriever = MultiQueryRetriever(...)
    deduped = retriever.deduplicate_by_doi(docs)
    
    assert len(deduped) == 2
    assert deduped[0]["metadata"]["doi"] == "10.1021/abc"
    assert deduped[0]["score"] == 0.8  # 保留最高分

def test_reranking_order():
    """测试重排序"""
    candidates = [...]  # 候选文献
    reranker = SentenceReranker(...)
    
    reranked = reranker.rerank("压实密度", candidates, top_k=5)
    
    # 验证排序是降序的
    for i in range(len(reranked) - 1):
        assert reranked[i]["rerank_score"] >= reranked[i+1]["rerank_score"]
```

### Property-Based Tests

**测试框架**: Hypothesis (Python)

**Property 1: Query expansion preserves original**
```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=100))
def test_expansion_preserves_original(query):
    """Property: 扩展后的查询列表应包含原始查询"""
    expander = QueryExpander()
    result = expander.expand(query)
    
    assert query in result.all_queries
    assert result.all_queries[0] == query
```

**Property 2: Deduplication is idempotent**
```python
@given(st.lists(st.dictionaries(...)))
def test_deduplication_idempotent(documents):
    """Property: 去重操作是幂等的"""
    retriever = MultiQueryRetriever(...)
    
    deduped_once = retriever.deduplicate_by_doi(documents)
    deduped_twice = retriever.deduplicate_by_doi(deduped_once)
    
    assert deduped_once == deduped_twice
```

**Property 3: Reranking preserves count**
```python
@given(st.lists(st.dictionaries(...), min_size=1, max_size=50))
def test_reranking_preserves_count(candidates):
    """Property: 重排序不改变文档数量"""
    reranker = SentenceReranker(...)
    
    reranked = reranker.rerank("test query", candidates)
    
    assert len(reranked) <= len(candidates)
```

**Property 4: Similarity is bounded**
```python
@given(st.text(), st.text())
def test_similarity_bounded(query, sentence):
    """Property: 相似度在[0,1]范围内"""
    reranker = SentenceReranker(...)
    
    similarity = reranker.compute_similarity(query, sentence)
    
    assert 0.0 <= similarity <= 1.0
```

### Integration Tests

**测试场景**:
1. 端到端测试：从用户问题到最终结果
2. 性能测试：验证响应时间<10秒
3. 召回率测试：对比改进前后的召回率
4. 精确度测试：验证top-k的相关性

**测试用例**:
```python
def test_end_to_end_compaction_density():
    """测试"压实密度"问题的端到端流程"""
    expert = SemanticExpert(...)
    
    result = expert.search_with_expansion(
        question="磷酸铁锂的压实密度是多少？",
        top_k=15
    )
    
    assert result["success"]
    assert len(result["documents"]) > 0
    
    # 验证是否包含相关DOI
    dois = [doc["metadata"]["doi"] for doc in result["documents"]]
    assert "10.1021/acsaem.1c03269" in dois  # 已知包含压实密度信息的文献

def test_performance():
    """测试性能"""
    import time
    
    expert = SemanticExpert(...)
    
    start = time.time()
    result = expert.search_with_expansion("磷酸铁锂 导电率")
    elapsed = time.time() - start
    
    assert elapsed < 10.0  # 响应时间<10秒
```

## Performance Considerations

### 1. 批量API调用

**优化**: 批量生成embedding，减少API调用次数

```python
# 优化前：3次API调用
for query in queries:
    embedding = generate_embedding(query)

# 优化后：1次API调用
embeddings = generate_embeddings_batch(queries)
```

**预期提升**: API调用次数减少67%

### 2. 并行查询

**优化**: 使用线程池并行执行多个查询

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(retrieve, q) for q in queries]
    results = [f.result() for f in futures]
```

**预期提升**: 检索时间减少50%

### 3. 结果缓存

**优化**: 缓存重排序结果，避免重复计算

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def compute_max_sentence_similarity(query_hash, doi):
    # 计算相似度
    pass
```

**预期提升**: 重复查询响应时间减少80%

### 4. 限制候选数量

**优化**: 只对前20个候选进行重排序

```python
if len(candidates) > 20:
    candidates_to_rerank = candidates[:20]
else:
    candidates_to_rerank = candidates
```

**预期提升**: 重排序时间减少50%

## Configuration

### 配置文件格式

```python
# backend/config/settings.py

class Settings:
    # 查询扩展配置
    enable_query_expansion: bool = True
    enable_reranking: bool = True
    max_queries: int = 3
    
    # 重排序配置
    rerank_top_k: int = 20  # 只对前20个候选重排序
    rerank_timeout: int = 5  # 重排序超时（秒）
    
    # 术语映射表路径
    term_mapping_file: str = "config/term_mapping.json"
    synonym_file: str = "config/synonyms.json"
```

### 术语映射表

```json
{
  "磷酸铁锂": "LiFePO4",
  "压实密度": "compaction density",
  "电极密度": "electrode density",
  "导电率": "conductivity",
  "比容量": "specific capacity",
  "循环性能": "cycling performance",
  "碳包覆": "carbon coating",
  "离子掺杂": "ion doping"
}
```

### 同义词库

```json
{
  "压实密度": ["电极密度", "压制密度", "堆积密度"],
  "导电率": ["电导率", "电子电导", "离子电导"],
  "比容量": ["放电容量", "充电容量", "理论容量"],
  "循环性能": ["循环稳定性", "循环寿命", "容量保持率"]
}
```

## Migration Plan

### Phase 1: 实现核心组件（1-2天）

1. 实现 QueryExpander
2. 实现 MultiQueryRetriever
3. 实现 SentenceReranker
4. 单元测试

### Phase 2: 集成到 SemanticExpert（1天）

1. 添加 search_with_expansion() 方法
2. 添加配置开关
3. 实现回退逻辑
4. 集成测试

### Phase 3: 测试和优化（1-2天）

1. 端到端测试
2. 性能测试
3. 召回率/精确度对比
4. 优化瓶颈

### Phase 4: 部署和监控（1天）

1. 更新配置文件
2. 部署到生产环境
3. 监控性能指标
4. 收集用户反馈

**总计**: 4-6天

## Rollback Plan

如果新功能出现问题，可以通过配置快速回退：

```python
# 关闭查询扩展和重排序
settings.enable_query_expansion = False
settings.enable_reranking = False
```

系统会自动回退到原有的 `search()` 方法。
