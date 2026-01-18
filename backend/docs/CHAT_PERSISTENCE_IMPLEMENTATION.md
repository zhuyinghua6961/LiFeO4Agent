# 聊天记录持久化实现文档

## 📋 项目概述

实现分用户、分对话的聊天记录持久化存储功能，采用 **MySQL（元数据） + JSON文件（消息内容）** 的混合存储方案。

**存储架构**：
```
MySQL (conversations表)  →  存储对话元数据（ID、标题、用户、时间、文件路径）
JSON文件 (chat_history/)  →  存储完整消息内容（用户消息、AI回复、步骤、引用）
```

**文件结构**：
```
chat_history/
├── user_1/
│   ├── conv_123.json
│   ├── conv_124.json
│   └── conv_125.json
├── user_2/
│   ├── conv_126.json
│   └── conv_127.json
└── ...
```

---

## 🎯 功能清单

### 阶段一：数据模型层 (Models)

#### 1.1 实体类 (entities.py)

- [ ] **1.1.1** 创建 `Conversation` 实体类
  - [ ] 定义字段：id, user_id, title, file_path, message_count, created_at, updated_at
  - [ ] 实现 `to_dict()` 方法
  - [ ] 实现 `from_dict()` 类方法
  - [ ] 添加字段验证

- [ ] **1.1.2** 创建 `Message` 实体类
  - [ ] 定义字段：role, content, timestamp
  - [ ] 定义字段：queryMode, expert（可选，仅bot消息）
  - [ ] 定义字段：steps（数组，保存处理步骤）
  - [ ] 定义字段：references（数组，保存参考文献）
  - [ ] 实现 `to_dict()` 方法
  - [ ] 实现 `from_dict()` 类方法

- [ ] **1.1.3** 创建 `Step` 实体类
  - [ ] 定义字段：step, message, status, data, error
  - [ ] 实现 `to_dict()` 方法
  - [ ] 实现 `from_dict()` 类方法

#### 1.2 DTO类 (dtos.py)

- [ ] **1.2.1** 创建 `ConversationCreateRequest` DTO
  - [ ] 定义字段：user_id, title（可选）
  - [ ] 实现 `validate()` 方法

- [ ] **1.2.2** 创建 `ConversationListResponse` DTO
  - [ ] 定义字段：conversations（数组）, total_count
  - [ ] 实现 `to_dict()` 方法

- [ ] **1.2.3** 创建 `ConversationDetailResponse` DTO
  - [ ] 定义字段：conversation_id, title, messages, created_at, updated_at
  - [ ] 实现 `to_dict()` 方法

- [ ] **1.2.4** 创建 `MessageAddRequest` DTO
  - [ ] 定义字段：role, content, steps, references
  - [ ] 实现 `validate()` 方法

- [ ] **1.2.5** 创建 `ConversationUpdateRequest` DTO
  - [ ] 定义字段：title
  - [ ] 实现 `validate()` 方法

---

### 阶段二：仓储层 (Repositories)

#### 2.1 数据库仓储 (conversation_repository.py)

- [ ] **2.1.1** 创建 `ConversationRepository` 类
  - [ ] 实现构造函数，初始化数据库连接

- [ ] **2.1.2** 实现 `create()` 方法
  - [ ] 插入对话记录到 conversations 表
  - [ ] 返回新创建的对话ID
  - [ ] 处理数据库异常

- [ ] **2.1.3** 实现 `get_by_id()` 方法
  - [ ] 根据对话ID查询单条记录
  - [ ] 返回 Conversation 实体
  - [ ] 处理不存在的情况

- [ ] **2.1.4** 实现 `get_by_user()` 方法
  - [ ] 根据用户ID查询所有对话
  - [ ] 按 updated_at 降序排序
  - [ ] 支持分页（offset, limit）
  - [ ] 返回 Conversation 实体列表

- [ ] **2.1.5** 实现 `update_title()` 方法
  - [ ] 更新对话标题
  - [ ] 自动更新 updated_at
  - [ ] 返回是否成功

- [ ] **2.1.6** 实现 `update_message_count()` 方法
  - [ ] 更新消息数量
  - [ ] 自动更新 updated_at
  - [ ] 返回是否成功

- [ ] **2.1.7** 实现 `delete()` 方法
  - [ ] 删除对话记录
  - [ ] 检查用户权限（只能删除自己的对话）
  - [ ] 返回是否成功

- [ ] **2.1.8** 实现 `exists()` 方法
  - [ ] 检查对话是否存在
  - [ ] 检查是否属于指定用户
  - [ ] 返回布尔值

- [ ] **2.1.9** 实现 `count_by_user()` 方法
  - [ ] 统计用户的对话总数
  - [ ] 返回整数

#### 2.2 文件仓储 (conversation_file_repository.py)

- [ ] **2.2.1** 创建 `ConversationFileRepository` 类
  - [ ] 定义基础路径常量 `CHAT_HISTORY_DIR`
  - [ ] 实现构造函数，确保目录存在

- [ ] **2.2.2** 实现 `_get_file_path()` 私有方法
  - [ ] 根据 user_id 和 conversation_id 生成文件路径
  - [ ] 格式：`chat_history/user_{user_id}/conv_{conv_id}.json`
  - [ ] 返回完整路径

- [ ] **2.2.3** 实现 `_ensure_user_dir()` 私有方法
  - [ ] 确保用户目录存在
  - [ ] 如果不存在则创建
  - [ ] 处理权限错误

- [ ] **2.2.4** 实现 `create()` 方法
  - [ ] 创建新的对话JSON文件
  - [ ] 初始化空消息数组
  - [ ] 写入基本元数据（conversation_id, user_id, title, created_at）
  - [ ] 处理文件写入异常

- [ ] **2.2.5** 实现 `read()` 方法
  - [ ] 读取对话JSON文件
  - [ ] 解析JSON内容
  - [ ] 返回消息列表
  - [ ] 处理文件不存在的情况
  - [ ] 处理JSON解析错误

- [ ] **2.2.6** 实现 `append_message()` 方法
  - [ ] 读取现有JSON文件
  - [ ] 追加新消息到 messages 数组
  - [ ] 更新 updated_at 时间戳
  - [ ] 写回JSON文件
  - [ ] 实现文件锁机制（防止并发写入）
  - [ ] 处理异常情况

- [ ] **2.2.7** 实现 `update_title()` 方法
  - [ ] 读取JSON文件
  - [ ] 更新 title 字段
  - [ ] 更新 updated_at 时间戳
  - [ ] 写回JSON文件
  - [ ] 处理异常情况

- [ ] **2.2.8** 实现 `delete()` 方法
  - [ ] 删除对话JSON文件
  - [ ] 检查文件是否存在
  - [ ] 处理删除失败的情况
  - [ ] 返回是否成功

- [ ] **2.2.9** 实现 `exists()` 方法
  - [ ] 检查JSON文件是否存在
  - [ ] 返回布尔值

- [ ] **2.2.10** 实现 `get_file_size()` 方法
  - [ ] 获取JSON文件大小
  - [ ] 用于监控文件大小
  - [ ] 返回字节数

---

### 阶段三：服务层 (Services)

#### 3.1 对话服务 (conversation_service.py)

- [ ] **3.1.1** 创建 `ConversationService` 类
  - [ ] 注入 `ConversationRepository` 依赖
  - [ ] 注入 `ConversationFileRepository` 依赖
  - [ ] 实现构造函数

- [ ] **3.1.2** 实现 `create_conversation()` 方法
  - [ ] 验证用户ID
  - [ ] 生成默认标题（如果未提供）
  - [ ] 调用数据库仓储创建记录
  - [ ] 生成文件路径
  - [ ] 调用文件仓储创建JSON文件
  - [ ] 更新数据库中的 file_path
  - [ ] 返回对话ID和详情
  - [ ] 实现事务回滚（如果任一步骤失败）

- [ ] **3.1.3** 实现 `get_conversation_list()` 方法
  - [ ] 验证用户ID
  - [ ] 调用数据库仓储获取对话列表
  - [ ] 支持分页参数
  - [ ] 返回对话元数据列表（不含消息内容）
  - [ ] 处理异常情况

- [ ] **3.1.4** 实现 `get_conversation_detail()` 方法
  - [ ] 验证用户ID和对话ID
  - [ ] 从数据库获取对话元数据
  - [ ] 检查对话是否属于该用户
  - [ ] 从JSON文件读取完整消息
  - [ ] 合并元数据和消息内容
  - [ ] 返回完整对话详情
  - [ ] 处理文件不存在的情况

- [ ] **3.1.5** 实现 `add_message()` 方法
  - [ ] 验证用户ID和对话ID
  - [ ] 验证消息内容
  - [ ] 调用文件仓储追加消息
  - [ ] 更新数据库中的 message_count
  - [ ] 更新数据库中的 updated_at
  - [ ] 如果是第一条消息，自动生成标题
  - [ ] 返回是否成功
  - [ ] 处理异常情况

- [ ] **3.1.6** 实现 `update_conversation_title()` 方法
  - [ ] 验证用户ID和对话ID
  - [ ] 验证标题内容
  - [ ] 同时更新数据库和JSON文件
  - [ ] 返回是否成功
  - [ ] 处理异常情况

- [ ] **3.1.7** 实现 `delete_conversation()` 方法
  - [ ] 验证用户ID和对话ID
  - [ ] 检查对话是否属于该用户
  - [ ] 先删除JSON文件
  - [ ] 再删除数据库记录
  - [ ] 返回是否成功
  - [ ] 处理部分删除失败的情况

- [ ] **3.1.8** 实现 `get_conversation_count()` 方法
  - [ ] 验证用户ID
  - [ ] 调用数据库仓储统计数量
  - [ ] 返回对话总数

- [ ] **3.1.9** 实现 `_generate_title_from_message()` 私有方法
  - [ ] 从第一条用户消息生成标题
  - [ ] 截取前30个字符
  - [ ] 如果超过30字符，添加省略号
  - [ ] 返回标题字符串

- [ ] **3.1.10** 实现 `_validate_user_permission()` 私有方法
  - [ ] 检查对话是否属于指定用户
  - [ ] 抛出权限异常（如果不匹配）

---

### 阶段四：API层 (Routes)

#### 4.1 对话路由 (conversation_routes.py)

- [ ] **4.1.1** 创建对话蓝图
  - [ ] 创建 Blueprint：`conversation_bp`
  - [ ] 设置 URL 前缀：`/api/conversations`
  - [ ] 配置 CORS

- [ ] **4.1.2** 实现 `POST /api/conversations` - 创建新对话
  - [ ] 获取请求体（user_id, title）
  - [ ] 验证请求参数
  - [ ] 调用 `ConversationService.create_conversation()`
  - [ ] 返回 201 状态码和对话详情
  - [ ] 处理异常并返回错误响应

- [ ] **4.1.3** 实现 `GET /api/conversations` - 获取对话列表
  - [ ] 获取查询参数（user_id, page, page_size）
  - [ ] 验证用户ID
  - [ ] 调用 `ConversationService.get_conversation_list()`
  - [ ] 返回 200 状态码和对话列表
  - [ ] 处理异常并返回错误响应

- [ ] **4.1.4** 实现 `GET /api/conversations/{id}` - 获取对话详情
  - [ ] 获取路径参数（conversation_id）
  - [ ] 获取查询参数（user_id）
  - [ ] 验证参数
  - [ ] 调用 `ConversationService.get_conversation_detail()`
  - [ ] 返回 200 状态码和完整对话
  - [ ] 处理对话不存在的情况（404）
  - [ ] 处理权限错误（403）

- [ ] **4.1.5** 实现 `POST /api/conversations/{id}/messages` - 添加消息
  - [ ] 获取路径参数（conversation_id）
  - [ ] 获取请求体（user_id, message）
  - [ ] 验证消息格式（role, content, steps, references）
  - [ ] 调用 `ConversationService.add_message()`
  - [ ] 返回 201 状态码
  - [ ] 处理异常并返回错误响应

- [ ] **4.1.6** 实现 `PUT /api/conversations/{id}` - 更新对话标题
  - [ ] 获取路径参数（conversation_id）
  - [ ] 获取请求体（user_id, title）
  - [ ] 验证参数
  - [ ] 调用 `ConversationService.update_conversation_title()`
  - [ ] 返回 200 状态码
  - [ ] 处理异常并返回错误响应

- [ ] **4.1.7** 实现 `DELETE /api/conversations/{id}` - 删除对话
  - [ ] 获取路径参数（conversation_id）
  - [ ] 获取查询参数（user_id）
  - [ ] 验证参数
  - [ ] 调用 `ConversationService.delete_conversation()`
  - [ ] 返回 204 状态码（无内容）
  - [ ] 处理对话不存在的情况（404）
  - [ ] 处理权限错误（403）

- [ ] **4.1.8** 注册蓝图到主应用
  - [ ] 在 `main.py` 中导入 `conversation_bp`
  - [ ] 调用 `app.register_blueprint(conversation_bp)`

#### 4.2 集成到现有问答流程

- [ ] **4.2.1** 修改 `POST /api/ask_stream` 接口
  - [ ] 接收额外参数：user_id, conversation_id
  - [ ] 如果 conversation_id 为空，自动创建新对话
  - [ ] 在流式响应开始前，保存用户消息
  - [ ] 在流式响应完成后，保存AI回复（包含steps）
  - [ ] 保持向后兼容（参数可选）

---

### 阶段五：前端改造 (Frontend)

#### 5.1 API服务层 (api.js)

- [ ] **5.1.1** 添加对话管理API方法
  - [ ] 实现 `createConversation(userId, title)` 方法
  - [ ] 实现 `getConversationList(userId, page, pageSize)` 方法
  - [ ] 实现 `getConversationDetail(conversationId, userId)` 方法
  - [ ] 实现 `addMessage(conversationId, userId, message)` 方法
  - [ ] 实现 `updateConversationTitle(conversationId, userId, title)` 方法
  - [ ] 实现 `deleteConversation(conversationId, userId)` 方法

- [ ] **5.1.2** 修改 `askStream()` 方法
  - [ ] 添加 userId 和 conversationId 参数
  - [ ] 在请求体中包含这些参数
  - [ ] 保持向后兼容

#### 5.2 Store层 (chatStore.js)

- [ ] **5.2.1** 添加用户状态管理
  - [ ] 添加 `userId` 状态
  - [ ] 添加 `setUserId()` 方法
  - [ ] 从 localStorage 或登录状态获取 userId

- [ ] **5.2.2** 修改对话加载逻辑
  - [ ] 修改 `loadChats()` 方法，从服务器加载
  - [ ] 调用 `api.getConversationList(userId)`
  - [ ] 保留 localStorage 作为离线缓存
  - [ ] 实现服务器优先策略

- [ ] **5.2.3** 修改对话创建逻辑
  - [ ] 修改 `createNewChat()` 方法
  - [ ] 调用 `api.createConversation(userId)`
  - [ ] 获取服务器返回的 conversation_id
  - [ ] 同步到 localStorage

- [ ] **5.2.4** 修改消息保存逻辑
  - [ ] 修改 `addUserMessage()` 方法
  - [ ] 调用 `api.addMessage()` 同步到服务器
  - [ ] 保留 localStorage 同步
  - [ ] 实现乐观更新（先更新UI，后台同步）

- [ ] **5.2.5** 修改对话删除逻辑
  - [ ] 修改 `deleteChat()` 方法
  - [ ] 调用 `api.deleteConversation()`
  - [ ] 同步删除 localStorage
  - [ ] 处理删除失败的情况

- [ ] **5.2.6** 添加同步状态管理
  - [ ] 添加 `syncStatus` 状态（synced/syncing/failed）
  - [ ] 添加同步失败重试机制
  - [ ] 显示同步状态图标

#### 5.3 UI层 (Home.vue)

- [ ] **5.3.1** 修改发送消息逻辑
  - [ ] 在 `sendMessage()` 中传递 userId 和 conversationId
  - [ ] 调用修改后的 `api.askStream()`
  - [ ] 处理自动创建对话的情况

- [ ] **5.3.2** 添加同步状态显示
  - [ ] 在对话列表项显示同步状态图标
  - [ ] 云图标（已同步）
  - [ ] 旋转图标（同步中）
  - [ ] 警告图标（同步失败）

- [ ] **5.3.3** 添加离线提示
  - [ ] 检测网络状态
  - [ ] 离线时显示提示信息
  - [ ] 离线时禁用某些功能

---

### 阶段六：测试与优化

#### 6.1 单元测试

- [ ] **6.1.1** 测试 `ConversationRepository`
  - [ ] 测试创建对话
  - [ ] 测试查询对话
  - [ ] 测试更新对话
  - [ ] 测试删除对话
  - [ ] 测试权限检查

- [ ] **6.1.2** 测试 `ConversationFileRepository`
  - [ ] 测试创建JSON文件
  - [ ] 测试读取JSON文件
  - [ ] 测试追加消息
  - [ ] 测试并发写入
  - [ ] 测试文件锁机制

- [ ] **6.1.3** 测试 `ConversationService`
  - [ ] 测试完整的创建流程
  - [ ] 测试消息添加流程
  - [ ] 测试事务回滚
  - [ ] 测试权限验证

#### 6.2 集成测试

- [ ] **6.2.1** 测试API端点
  - [ ] 测试创建对话接口
  - [ ] 测试获取对话列表接口
  - [ ] 测试获取对话详情接口
  - [ ] 测试添加消息接口
  - [ ] 测试更新标题接口
  - [ ] 测试删除对话接口

- [ ] **6.2.2** 测试前后端集成
  - [ ] 测试完整的对话流程
  - [ ] 测试步骤保存和显示
  - [ ] 测试引用保存和显示
  - [ ] 测试跨设备同步

#### 6.3 性能优化

- [ ] **6.3.1** 数据库优化
  - [ ] 添加必要的索引
  - [ ] 优化查询语句
  - [ ] 实现连接池

- [ ] **6.3.2** 文件操作优化
  - [ ] 实现文件缓存
  - [ ] 优化大文件读写
  - [ ] 实现异步写入

- [ ] **6.3.3** 前端优化
  - [ ] 实现虚拟滚动（长对话列表）
  - [ ] 实现消息懒加载
  - [ ] 优化 localStorage 使用

#### 6.4 错误处理

- [ ] **6.4.1** 后端错误处理
  - [ ] 统一错误响应格式
  - [ ] 添加详细的错误日志
  - [ ] 实现错误监控

- [ ] **6.4.2** 前端错误处理
  - [ ] 添加错误提示UI
  - [ ] 实现自动重试机制
  - [ ] 添加错误上报

---

### 阶段七：文档与部署

#### 7.1 文档编写

- [ ] **7.1.1** API文档
  - [ ] 编写接口说明
  - [ ] 添加请求示例
  - [ ] 添加响应示例
  - [ ] 说明错误码

- [ ] **7.1.2** 数据库文档
  - [ ] 说明表结构
  - [ ] 说明索引设计
  - [ ] 说明数据迁移

- [ ] **7.1.3** 文件存储文档
  - [ ] 说明目录结构
  - [ ] 说明JSON格式
  - [ ] 说明备份策略

#### 7.2 部署准备

- [ ] **7.2.1** 数据库迁移
  - [ ] 确认 conversations 表已创建
  - [ ] 添加必要的索引
  - [ ] 测试数据库连接

- [ ] **7.2.2** 文件系统准备
  - [ ] 创建 chat_history 目录
  - [ ] 设置目录权限
  - [ ] 配置备份策略

- [ ] **7.2.3** 配置管理
  - [ ] 添加配置项到 settings.py
  - [ ] 配置文件存储路径
  - [ ] 配置文件大小限制

---

## 📊 进度追踪

### 总体进度
- **阶段一（数据模型层）**：0/13 (0%)
- **阶段二（仓储层）**：0/19 (0%)
- **阶段三（服务层）**：0/10 (0%)
- **阶段四（API层）**：0/9 (0%)
- **阶段五（前端改造）**：0/14 (0%)
- **阶段六（测试与优化）**：0/14 (0%)
- **阶段七（文档与部署）**：0/6 (0%)

**总计**：0/85 (0%)

---

## 🎯 实施建议

### 开发顺序
1. **先后端后前端**：确保后端API稳定后再改造前端
2. **先核心后扩展**：优先实现创建、读取、删除功能
3. **先功能后优化**：功能完成后再进行性能优化
4. **增量开发**：每完成一个小功能就测试并标记完成

### 测试策略
- 每个阶段完成后进行单元测试
- 阶段四完成后进行集成测试
- 全部完成后进行端到端测试

### 风险控制
- 保持向后兼容，不影响现有功能
- 实现数据备份机制
- 添加详细的错误日志
- 实现数据迁移脚本（如需要）

---

## 📝 注意事项

1. **并发控制**：文件写入需要实现锁机制
2. **文件大小**：监控JSON文件大小，超长对话需要分片
3. **权限检查**：所有操作都要验证用户权限
4. **事务一致性**：数据库和文件操作要保持一致
5. **向后兼容**：保留 localStorage 作为离线缓存
6. **步骤完整性**：确保步骤信息完整保存
7. **引用完整性**：确保参考文献信息完整保存

---

## 🔄 更新日志

- **2024-01-18**：创建初始实现文档，拆分85个小功能点
