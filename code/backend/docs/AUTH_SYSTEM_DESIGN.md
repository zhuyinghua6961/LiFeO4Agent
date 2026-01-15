# 用户认证系统设计文档

## 1. 数据库设计

### 1.1 用户表 (users)

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '加密后的密码',
    role ENUM('user', 'admin') NOT NULL DEFAULT 'user' COMMENT '角色',
    status ENUM('active', 'disabled') NOT NULL DEFAULT 'active' COMMENT '账号状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
```

### 1.2 字段说明

| 字段 | 说明 |
|------|------|
| `id` | 用户唯一ID |
| `username` | 用户名，唯一 |
| `password` | bcrypt加密后的密码 |
| `role` | 角色: user/admin |
| `status` | 状态: active/disabled |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

### 1.3 账号状态说明

| 状态 | 说明 |
|------|------|
| `active` | 正常使用 |
| `disabled` | 已停用，无法登录 |

### 1.4 预设管理员账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | admin |

> 首次启动时自动创建管理员账号

---

## 2. API 接口设计

### 2.1 基础信息

- **Base URL**: `/api/auth`
- **Content-Type**: `application/json`
- **认证方式**: JWT Token (存放在 Header: `Authorization: Bearer <token>`)

### 2.2 接口列表

#### 2.2.1 用户登录

```
POST /api/auth/login
```

**请求体**:
```json
{
    "username": "admin",
    "password": "admin123"
}
```

**响应** (成功):
```json
{
    "success": true,
    "message": "登录成功",
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "user": {
            "id": 1,
            "username": "admin",
            "role": "admin"
        }
    }
}
```

**响应** (失败):
```json
{
    "success": false,
    "error": "用户名或密码错误",
    "code": "INVALID_CREDENTIALS"
}
```

#### 2.2.2 用户注册

```
POST /api/auth/register
```

**请求体**:
```json
{
    "username": "newuser",
    "password": "password123"
}
```

**响应**:
```json
{
    "success": true,
    "message": "注册成功",
    "data": {
        "id": 2,
        "username": "newuser",
        "role": "user"
    }
}
```

#### 2.2.3 获取当前用户信息

```
GET /api/auth/me
```

**请求头**:
```
Authorization: Bearer <token>
```

**响应**:
```json
{
    "success": true,
    "data": {
        "id": 1,
        "username": "admin",
        "role": "admin",
        "created_at": "2024-01-15T10:00:00"
    }
}
```

#### 2.2.4 修改密码

```
PUT /api/auth/password
```

**请求头**:
```
Authorization: Bearer <token>
```

**请求体**:
```json
{
    "old_password": "old123",
    "new_password": "new123"
}
```

**响应**:
```json
{
    "success": true,
    "message": "密码修改成功"
}
```

#### 2.2.5 用户登出

```
POST /api/auth/logout
```

**响应**:
```json
{
    "success": true,
    "message": "登出成功"
}
```

---

## 3. 管理员专用接口

### 3.1 接口前缀

所有管理员接口使用前缀：`/api/admin`

### 3.2 接口列表

#### 3.2.1 获取所有用户列表（管理员）

```
GET /api/admin/users
```

**请求头**:
```
Authorization: Bearer <token>  (需要 admin 角色)
```

**响应**:
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "username": "admin",
            "role": "admin",
            "status": "active",
            "created_at": "2024-01-15T10:00:00"
        },
        {
            "id": 2,
            "username": "user1",
            "role": "user",
            "status": "active",
            "created_at": "2024-01-15T11:00:00"
        }
    ]
}
```

#### 3.2.2 修改任意用户密码（管理员）

```
PUT /api/admin/users/<user_id>/password
```

**请求体**:
```json
{
    "new_password": "newpassword123"
}
```

**响应**:
```json
{
    "success": true,
    "message": "用户密码已修改"
}
```

#### 3.2.3 停用/启用用户（管理员）

```
PUT /api/admin/users/<user_id>/status
```

**请求体**:
```json
{
    "status": "disabled"  // 或 "active"
}
```

**响应**:
```json
{
    "success": true,
    "message": "用户已停用"
}
```

#### 3.2.4 删除用户（管理员）

```
DELETE /api/admin/users/<user_id>
```

**响应**:
```json
{
    "success": true,
    "message": "用户已删除"
}
```

---

## 4. 前端页面规划

### 4.1 页面结构

```
code/frontend-vue/src/
├── views/
│   ├── Login.vue          # 登录页
│   ├── Register.vue       # 注册页
│   ├── UserDashboard.vue  # 用户首页
│   └── AdminDashboard.vue # 管理员首页
└── router/
    └── index.js           # 路由配置
```

### 4.2 路由配置

```javascript
const routes = [
    { path: '/login', component: Login },
    { path: '/register', component: Register },
    { path: '/user', component: UserDashboard, meta: { requiresAuth: true, role: 'user' } },
    { path: '/admin', component: AdminDashboard, meta: { requiresAuth: true, role: 'admin' } },
    { path: '/', redirect: '/login' }
]
```

### 4.3 页面功能

#### 登录页 (Login.vue)
- 用户名输入框
- 密码输入框
- 登录按钮
- 注册链接

#### 注册页 (Register.vue)
- 用户名输入框
- 密码输入框
- 确认密码输入框
- 注册按钮
- 登录链接

#### 用户首页 (UserDashboard.vue)
- 欢迎信息
- 修改密码表单
- 登出按钮

#### 管理员首页 (AdminDashboard.vue)
- 用户列表
- 修改用户密码
- 停用/启用用户
- 删除用户
- 登出按钮

---

## 5. 技术实现

### 5.1 后端依赖

```
Flask==3.0.0
PyMySQL==1.1.0
bcrypt==4.1.2
```

> 注：简化版使用手动 JWT 实现，不使用 Flask-JWT-Extended

### 5.2 目录结构

```
code/backend/
├── api/
│   ├── __init__.py
│   ├── routes.py          # 现有路由
│   └── auth_routes.py     # 认证路由 (新建)
├── models/
│   ├── __init__.py
│   └── user.py            # 用户模型 (新建)
├── services/
│   ├── __init__.py
│   └── auth_service.py    # 认证服务 (新建)
└── database/
    ├── __init__.py
    └── connection.py      # 数据库连接 (新建)
```

### 5.3 JWT 实现

```python
import jwt
import time

JWT_SECRET = "your-secret-key"
JWT_EXPIRE = 24 * 3600  # 24小时

def create_token(user_id, role):
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": time.time() + JWT_EXPIRE
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
```

### 5.4 MySQL 配置

```python
# config.env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=Zhuyinghua123..
MYSQL_DATABASE=material_kb
```

---

## 6. 错误码说明

| 错误码 | 说明 |
|--------|------|
| `INVALID_CREDENTIALS` | 用户名或密码错误 |
| `ACCOUNT_DISABLED` | 账号已停用 |
| `USERNAME_EXISTS` | 用户名已存在 |
| `INVALID_PASSWORD` | 旧密码错误 |
| `PERMISSION_DENIED` | 权限不足 |
| `TOKEN_EXPIRED` | Token过期 |
| `TOKEN_INVALID` | Token无效 |

---

## 7. 开发计划

### Phase 1: 后端实现
- [ ] 创建数据库表
- [ ] 实现数据库连接
- [ ] 实现用户模型
- [ ] 实现认证服务
- [ ] 实现认证路由
- [ ] 实现管理员路由
- [ ] 创建预设管理员账号

### Phase 2: 前端实现
- [ ] 创建登录页面
- [ ] 创建注册页面
- [ ] 创建用户首页
- [ ] 创建管理员首页
- [ ] 配置路由守卫

---

---

## 9. 问答记录存储设计

### 9.1 设计思路

采用 **混合存储** 方案：
- **数据库**：存储对话元数据（用户、标题、时间、文件路径）
- **文件**：存储完整的对话记录（JSON格式）

### 9.2 目录结构

```
code/
├── conversations/                    # 对话文件存储目录
│   ├── user_1/                       # 用户1的对话目录
│   │   ├── conversation_1.json       # 对话1的完整记录
│   │   ├── conversation_2.json       # 对话2的完整记录
│   │   └── ...
│   └── user_2/
│       ├── conversation_3.json
│       └── ...
```

### 9.3 数据库设计

```sql
-- 对话会话表
CREATE TABLE conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    title VARCHAR(255) COMMENT '对话标题(首条提问)',
    file_path VARCHAR(500) COMMENT '对话文件路径',
    message_count INT DEFAULT 0 COMMENT '消息数量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后消息时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话会话表';
```

### 9.4 对话文件格式

```json
{
    "conversation_id": 1,
    "user_id": 1,
    "title": "磷酸铁锂的电压是多少",
    "messages": [
        {
            "role": "user",
            "content": "磷酸铁锂的电压是多少",
            "timestamp": "2024-01-15T10:00:00"
        },
        {
            "role": "assistant",
            "content": "磷酸铁锂(LiFePO4)的标称电压为3.2V...",
            "timestamp": "2024-01-15T10:00:01",
            "metadata": {
                "expert": "literature",
                "references": [...]
            }
        },
        {
            "role": "user",
            "content": "那充电电压范围呢",
            "timestamp": "2024-01-15T10:05:00"
        }
    ],
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:10:00"
}
```

### 9.5 API 设计

#### 创建新对话（用户开始提问时调用）

```
POST /api/conversations
```

**请求体**:
```json
{
    "title": "磷酸铁锂的电压是多少"
}
```

**响应**:
```json
{
    "success": true,
    "data": {
        "id": 1,
        "title": "磷酸铁锂的电压是多少",
        "file_path": "conversations/user_1/conversation_1.json"
    }
}
```

#### 获取对话列表

```
GET /api/conversations
```

**响应**:
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "title": "磷酸铁锂的电压是多少",
            "message_count": 5,
            "updated_at": "2024-01-15T10:05:00"
        },
        {
            "id": 2,
            "title": "锂电池的工作原理",
            "message_count": 3,
            "updated_at": "2024-01-16T14:00:00"
        }
    ]
}
```

#### 获取对话详情

```
GET /api/conversations/<conversation_id>
```

**响应**: 返回完整的对话文件内容

#### 删除对话

```
DELETE /api/conversations/<conversation_id>
```

**响应**:
```json
{
    "success": true,
    "message": "对话已删除"
}
```

#### 搜索对话

```
GET /api/conversations/search?keyword=磷酸铁锂
```

**Query参数**:
- `keyword`: 搜索关键词
- `page`: 页码，默认1
- `page_size`: 每页数量，默认10

**响应**:
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "title": "磷酸铁锂的电压是多少",
            "message_count": 5,
            "highlight": "...磷酸铁锂的<em>电压</em>是多少...",
            "updated_at": "2024-01-15T10:05:00"
        }
    ],
    "pagination": {
        "page": 1,
        "page_size": 10,
        "total": 1
    }
}
```

### 9.6 核心服务设计

```python
# services/conversation_service.py

class ConversationService:
    """对话服务"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.conversations_dir = Path("conversations") / f"user_{user_id}"
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
    
    def create_conversation(self, title: str) -> Conversation:
        """创建新对话"""
        # 1. 创建文件
        conv_id = self._generate_id()
        file_path = self.conversations_dir / f"conversation_{conv_id}.json"
        
        # 2. 写入空对话文件
        conversation = {
            "conversation_id": conv_id,
            "user_id": self.user_id,
            "title": title[:100],  # 标题限制100字
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._write_file(file_path, conversation)
        
        # 3. 写入数据库
        db_conv = Conversation(
            user_id=self.user_id,
            title=title[:100],
            file_path=str(file_path),
            message_count=0
        )
        db_conv.save()
        
        return db_conv
    
    def add_message(self, conversation_id: int, role: str, content: str, metadata: dict = None):
        """添加消息到对话"""
        file_path = self._get_file_path(conversation_id)
        conversation = self._read_file(file_path)
        
        # 添加消息
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            message["metadata"] = metadata
        
        conversation["messages"].append(message)
        conversation["updated_at"] = datetime.now().isoformat()
        
        # 写回文件
        self._write_file(file_path, conversation)
        
        # 更新数据库
        self._update_db_count(conversation_id, len(conversation["messages"]))
    
    def get_messages_for_llm(self, conversation_id: int, limit: int = 10) -> List[Dict]:
        """获取用于LLM的历史消息（最近N条）"""
        conversation = self._read_file(self._get_file_path(conversation_id))
        messages = conversation["messages"][-limit:]
        # 转换为LLM格式
        return [{"role": m["role"], "content": m["content"]} for m in messages]
```

### 9.7 改造现有接口

改造 `ask_stream` 接口，支持保存对话记录：

```python
@api.route('/ask_stream', methods=['POST'])
def ask_stream():
    """问答流式接口 - 支持对话保存"""
    data = request.get_json()
    conversation_id = data.get('conversation_id')  # 可选，新对话不传
    ...
    
    def generate():
        # 如果没有conversation_id，先创建对话
        if not conversation_id:
            conv_service = ConversationService(user_id=get_current_user_id())
            conversation = conv_service.create_conversation(question)
            conversation_id = conversation.id
            # 发送对话ID给前端
            yield f"data: {json.dumps({'type': 'conversation_id', 'id': conversation_id})}\n\n"
        
        conv_service = ConversationService(user_id=get_current_user_id())
        
        # 保存用户提问
        conv_service.add_message(conversation_id, "user", question)
        
        # 获取历史消息
        history = conv_service.get_messages_for_llm(conversation_id, limit=10)
        
        # 流式查询...
        for chunk in integrated_agent.query_stream(question, chat_history=history):
            yield f"data: {json.dumps(chunk)}\n\n"
            
            # 如果是最终答案，保存到文件
            if chunk.get('type') == 'done':
                conv_service.add_message(
                    conversation_id, 
                    "assistant", 
                    chunk.get('full_answer', ''),
                    metadata={"references": chunk.get('references')}
                )
```

### 9.8 对话搜索实现

```python
# services/conversation_service.py 新增方法

def search_conversations(self, keyword: str, page: int = 1, page_size: int = 10) -> Dict:
    """搜索对话（标题和消息内容）"""
    import glob
    import re
    
    results = []
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    
    # 遍历用户的对话文件
    for file_path in self.conversations_dir.glob("conversation_*.json"):
        conversation = self._read_file(file_path)
        
        # 搜索标题
        title_match = pattern.search(conversation.get('title', ''))
        
        # 搜索消息内容
        message_matches = []
        for msg in conversation.get('messages', []):
            if pattern.search(msg.get('content', '')):
                message_matches.append(msg.get('content', '')[:200])
        
        if title_match or message_matches:
            # 生成高亮摘要
            highlight = ""
            if title_match:
                highlight = pattern.sub(
                    lambda m: f"<em>{m.group(0)}</em>",
                    conversation.get('title', '')
                )[:200]
            elif message_matches:
                highlight = pattern.sub(
                    lambda m: f"<em>{m.group(0)}</em>",
                    message_matches[0]
                )[:200]
            
            results.append({
                "id": conversation.get('conversation_id'),
                "title": conversation.get('title'),
                "message_count": len(conversation.get('messages', [])),
                "highlight": highlight,
                "updated_at": conversation.get('updated_at')
            })
    
    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        "data": results[start:end],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": len(results)
        }
    }
```

### 9.9 前端展示

**用户首页 (UserDashboard.vue)**：
- 左侧边栏：对话历史列表 + 搜索框
- 搜索框实时过滤对话列表
- 点击对话 → 加载完整记录并展示
- 新建对话按钮
- 删除对话按钮
- 高级搜索（弹窗）→ 搜索历史消息内容

---

## 10. 注意事项

1. **文件安全**: 验证用户只能访问自己的对话文件
2. **文件清理**: 删除对话时同时删除文件
3. **并发安全**: 写文件时加锁
4. **备份**: 定期备份 conversations 目录
5. **权限验证**: 每个接口都需要验证角色
