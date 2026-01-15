# 后端架构设计规范

## 项目结构

```
backend/
├── config/                    # 配置层 ✅ 已完成
│   ├── __init__.py
│   ├── settings.py           # 全局配置
│   └── prompts/              # 提示词模板
│       ├── __init__.py
│       ├── prompt_loader.py
│       ├── system_prompt.txt
│       ├── synthesis_prompt.txt
│       └── ...
│
├── services/                  # 服务层 ✅ 已完成
│   ├── __init__.py           # ✅ 已更新
│   ├── llm_service.py        # LLM服务 ✅ 原有
│   ├── neo4j_service.py      # Neo4j服务 ✅ 原有
│   └── vector_service.py     # ✅ 新建
│
├── agents/                    # 智能体层 ✅ 已完成
│   ├── __init__.py
│   └── experts/              # 专家系统 ✅ 已完成
│       ├── __init__.py       # ✅ 已更新
│       ├── router_expert.py  # ✅ 路由专家
│       ├── query_expert.py   # ✅ 精确查询专家
│       └── semantic_expert.py # ✅ 语义搜索专家
│
├── repositories/              # 数据访问层 ✅ 已完成
│   ├── __init__.py           # ✅ 已更新
│   ├── neo4j_repository.py   # ✅ 原有
│   └── vector_repository.py  # ✅ 原有
│
├── models/                    # 数据模型层 ✅ 已完成
│   ├── __init__.py           # ✅ 新建
│   ├── entities.py           # ✅ 新建
│   └── dtos.py               # ✅ 新建
│
├── utils/                     # 工具层 ✅ 已完成
│   ├── __init__.py           # ✅ 新建
│   ├── pdf_loader.py         # ✅ 新建
│   ├── cypher_utils.py       # ✅ 新建
│   └── formatters.py         # ✅ 新建
│
├── api/                       # API层 ✅ 已完成
│   ├── __init__.py           # ✅ 新建
│   └── routes.py             # ✅ 新建
│
├── main.py                    # ✅ 新建
│
├── scripts/                   # 脚本工具
│   ├── __init__.py
│   ├── init_db.py            # 数据库初始化
│   ├── test_connection.py    # 连接测试
│   └── manage_papers.py      # 文献管理
│
├── requirements.txt
├── config.env.example
└── __init__.py
```

## 层级说明

### 1. config/ (配置层) ✅ 已完成
- 全局配置管理 (`settings.py`)
- 提示词模板存储
- 环境变量加载

### 2. services/ (服务层) ✅ 已完成
| 服务 | 功能 | 依赖 |
|------|------|------|
| LLMService | LLM调用 | LangChain |
| Neo4jService | Neo4j业务逻辑 | Neo4jRepository |
| VectorService | 向量数据库操作 | VectorRepository, CommunityVectorRepository |

### 3. agents/ (智能体层) ✅ 已完成
| 专家类 | 功能 | 依赖 |
|--------|------|------|
| RouterExpert | 智能路由分析 | LLMService |
| QueryExpert | 精确查询（Cypher生成） | Neo4jService, LLMService |
| SemanticExpert | 语义搜索 | VectorRepository, LLMService |

### 4. repositories/ (数据访问层) ✅ 已完成
| 仓储 | 功能 | 数据库 |
|------|------|--------|
| Neo4jRepository | Neo4j操作 | Neo4j |
| VectorRepository | 文献向量 | ChromaDB |
| CommunityVectorRepository | 社区向量 | ChromaDB |

### 5. models/ (数据模型层) ✅ 已完成

**Entities (实体)**
- `Material` - 材料实体
- `Paper` - 文献实体
- `CommunitySummary` - 社区摘要实体
- `QueryResult` - 查询结果实体
- `RoutingDecision` - 路由决策实体
- `SearchResult` - 搜索结果实体

**DTOs (数据传输对象)**
- `QueryRequest/QueryResponse` - 查询请求/响应
- `RouteRequest/RouteResponse` - 路由请求/响应
- `SearchParams/SearchResponse` - 搜索请求/响应
- `MaterialQueryParams/MaterialQueryResult` - 材料查询
- `SynthesisRequest/SynthesisResponse` - 综合查询
- `HealthResponse` - 健康检查
- `ErrorResponse` - 错误响应

### 6. utils/ (工具层) ✅ 已完成
| 工具 | 功能 |
|------|------|
| PDFLoader | PDF文件加载和解析 |
| PDFBatchLoader | 批量PDF加载 |
| CypherGenerator | Cypher查询生成 |
| CypherOptimizer | Cypher查询优化 |
| CypherValidator | Cypher查询验证 |
| NumberFormatter | 数字格式化 |
| MaterialFormatter | 材料数据格式化 |
| PaperFormatter | 文献数据格式化 |
| JSONFormatter | JSON格式化 |
| TableFormatter | 表格格式化 |
| ResponseFormatter | API响应格式化 |

### 7. api/ (API层) ✅ 已完成

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/route` | POST | 路由查询 |
| `/api/query` | POST | 执行查询 |
| `/api/query/material` | POST | 材料精确查询 |
| `/api/search` | POST | 语义搜索 |
| `/api/aggregate` | POST | 聚合知识 |
| `/api/stats` | GET | 统计信息 |

### 8. main.py (应用入口) ✅ 已完成
- Flask应用创建
- 服务初始化
- 路由注册

## 重构进度

### ✅ 已完成 (100%)

**配置层**
- [x] `config/settings.py` - 全局配置

**服务层**
- [x] `services/llm_service.py` - LLM服务
- [x] `services/neo4j_service.py` - Neo4j服务
- [x] `services/vector_service.py` - 向量服务

**数据访问层**
- [x] `repositories/neo4j_repository.py` - Neo4j数据访问
- [x] `repositories/vector_repository.py` - 向量数据库访问

**智能体层**
- [x] `agents/experts/router_expert.py` - 路由专家
- [x] `agents/experts/query_expert.py` - 精确查询专家
- [x] `agents/experts/semantic_expert.py` - 语义搜索专家

**数据模型层**
- [x] `models/entities.py` - 数据实体
- [x] `models/dtos.py` - 数据传输对象

**工具层**
- [x] `utils/pdf_loader.py` - PDF工具
- [x] `utils/cypher_utils.py` - Cypher工具
- [x] `utils/formatters.py` - 格式化工具

**API层**
- [x] `api/routes.py` - API路由

**入口文件**
- [x] `main.py` - 应用入口

**初始化文件**
- [x] `config/__init__.py`
- [x] `services/__init__.py`
- [x] `repositories/__init__.py`
- [x] `agents/__init__.py`
- [x] `agents/experts/__init__.py`
- [x] `models/__init__.py`
- [x] `utils/__init__.py`
- [x] `api/__init__.py`

## 快速开始

```python
from backend.config.settings import settings
from backend.services import get_llm_service, get_neo4j_service, get_vector_service
from backend.agents.experts import RouterExpert, QueryExpert, SemanticExpert

# 初始化所有服务
llm = get_llm_service()
neo4j = get_neo4j_service()
vector = get_vector_service()

# 创建专家
router = RouterExpert(llm_service=llm)
query_expert = QueryExpert(neo4j_service=neo4j, llm_service=llm)
semantic_expert = SemanticExpert(vector_repo=vector._vector_repo, llm_service=llm)

# 使用
result = router.route("振实密度大于2.8的材料有哪些？")
print(result)
```

## 启动服务

```bash
cd code/backend
python main.py
```

## API 使用示例

```bash
# 健康检查
curl http://localhost:5000/api/health

# 路由查询
curl -X POST http://localhost:5000/api/route \
  -H "Content-Type: application/json" \
  -d '{"question": "振实密度大于2.8的材料有哪些？"}'

# 执行查询
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "振实密度大于2.8的材料有哪些？"}'

# 语义搜索
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "高导电性LiFePO4", "top_k": 10}'
```

## 导入规范

```python
# 推荐使用绝对导入
from backend.config.settings import settings
from backend.services import LLMService, get_llm_service
from backend.agents.experts import RouterExpert, QueryExpert, SemanticExpert
from backend.models import Material, QueryRequest, RouteResponse
from backend.utils import PDFLoader, CypherGenerator, NumberFormatter
```

## 命名规范

### 文件命名
- 使用小写字母和下划线：`neo4j_repository.py`
- 专家系统使用 `_expert.py` 后缀
- 脚本使用 `manage_`、`test_` 前缀

### 类命名
- 使用 PascalCase：`Neo4jService`
- 服务类使用 `Service` 后缀
- 专家类使用 `Expert` 后缀
- DTO类使用 `Request`/`Response` 后缀
- 工具类使用 `Formatter`/`Loader`/`Generator` 后缀

### 函数命名
- 使用 snake_case：`get_neo4j_repository`
- 私有方法使用 `_` 前缀
- 全局实例函数使用 `get_` 前缀

## 依赖注入

服务之间通过构造函数注入依赖：

```python
class QueryExpert:
    def __init__(self, neo4j_service: Neo4jService, llm_service: Optional[LLMService]):
        self._neo4j = neo4j_service
        self._llm = llm_service
```

## 异常处理

- 使用自定义异常类
- 在服务层捕获并记录
- 在API层转换为HTTP响应

```python
class BackendException(Exception):
    """基础异常类"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)
```

## 配置文件

使用 `config.env` 管理敏感配置：

```bash
# Neo4j连接
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# LLM API
DASHSCOPE_API_KEY=your_key
DASHSCOPE_MODEL=deepseek-v3.1

# 向量数据库
VECTOR_DB_PATH=./vector_database
COMMUNITY_DB_PATH=./community_database

# API服务
API_HOST=0.0.0.0
API_PORT=5000
DEBUG=True
```

## 注意事项

1. 所有新代码必须在 `code/backend` 目录下创建
2. 保持文件简洁，单个文件不超过500行
3. 及时更新本规范文档
4. 遵循 Python PEP 8 规范
5. 使用类型注解
6. 添加日志记录
7. 保持单向依赖（API → Services → Repositories）
