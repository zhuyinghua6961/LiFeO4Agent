# 用户类型系统说明

## 📋 系统概述

本系统实现了三级用户权限管理，通过 `user_type` 字段区分不同用户身份。

## 🎯 用户类型定义

| 用户身份 | user_type | role | 权限说明 |
|---------|-----------|------|---------|
| **管理员** | 1 | admin | 系统最高权限，可管理所有用户 |
| **超级用户** | 2 | super | 高级用户权限 |
| **普通用户** | 3 | user | 基础用户权限 |

## 🗄️ 数据库字段

### users 表结构

```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') NOT NULL DEFAULT 'user',
    status ENUM('active', 'disabled') NOT NULL DEFAULT 'active',
    user_type TINYINT NOT NULL DEFAULT 3 COMMENT '用户身份: 1=管理员, 2=超级用户, 3=普通用户',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    password_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    security_questions JSON,
    INDEX idx_status (status),
    INDEX idx_user_type (user_type)
);
```

### 字段说明

- **user_type**: 用户身份编码（1/2/3）
- **role**: 用户角色（admin/super/user）
- **status**: 账号状态（active/disabled）

## 💻 后端实现

### 1. 用户类型验证器

位置: `backend/services/user_data_validator.py`

```python
def map_user_type_to_code(self, user_type: str) -> int:
    """
    将用户身份字符串映射为数字编码
    
    Args:
        user_type: 用户身份字符串（super或common）
        
    Returns:
        用户身份编码（2=超级用户，3=普通用户，0=无效）
    """
    mapping = {
        'super': 2,
        'common': 3
    }
    return mapping.get(user_type.lower(), 0)
```

### 2. 创建用户接口

位置: `backend/api/admin_routes.py`

**接口**: `POST /api/admin/users`

**请求体**:
```json
{
    "username": "newuser",
    "password": "password123",
    "user_type": "super"  // 可选：super 或 common，默认 common
}
```

**响应**:
```json
{
    "success": true,
    "message": "用户 newuser 创建成功",
    "data": {
        "id": 3,
        "username": "newuser",
        "role": "super",
        "user_type": 2,
        "status": "active"
    }
}
```

### 3. 获取用户列表接口

位置: `backend/api/admin_routes.py`

**接口**: `GET /api/admin/users?page=1&page_size=10`

**响应**:
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "username": "admin",
            "role": "admin",
            "user_type": 1,
            "status": "active",
            "created_at": "2026-01-16T14:11:47"
        }
    ],
    "pagination": {
        "page": 1,
        "page_size": 10,
        "total": 1
    }
}
```

### 4. 批量导入用户

位置: `backend/services/batch_import_service.py`

**Excel 模板格式**:

| username | password | user_type |
|----------|----------|-----------|
| user001 | Pass123! | common |
| user002 | Test456@ | super |
| user003 | Demo789# | common |

**导入接口**: `POST /api/admin/users/batch-import`

## 🔐 权限控制

### 管理员权限装饰器

```python
@require_admin
def get_users():
    """只有管理员可以访问"""
    pass
```

### 权限检查逻辑

```python
# 检查是否是管理员
if payload.get('role') != 'admin':
    return jsonify({
        "success": False,
        "error": "权限不足，需要管理员权限",
        "code": "PERMISSION_DENIED"
    }), 403
```

## 📝 使用示例

### 1. 创建超级用户

```bash
curl -X POST http://localhost:5000/api/admin/users \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "superuser",
    "password": "Super123!",
    "user_type": "super"
  }'
```

### 2. 创建普通用户

```bash
curl -X POST http://localhost:5000/api/admin/users \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "normaluser",
    "password": "Normal123!",
    "user_type": "common"
  }'
```

### 3. 批量导入用户

```bash
curl -X POST http://localhost:5000/api/admin/users/batch-import \
  -H "Authorization: Bearer <admin_token>" \
  -F "file=@users.xlsx"
```

## 🔧 数据库维护

### 添加 user_type 字段

如果数据库中缺少 user_type 字段，运行以下脚本：

```bash
mysql -h 127.0.0.1 -u root -p material_kb < backend/scripts/add_user_type_field.sql
```

### 更新现有用户的 user_type

```sql
-- 管理员设置为 1
UPDATE users SET user_type = 1 WHERE role = 'admin';

-- 普通用户设置为 3
UPDATE users SET user_type = 3 WHERE role = 'user';
```

### 查询用户类型分布

```sql
SELECT 
    user_type,
    CASE user_type
        WHEN 1 THEN '管理员'
        WHEN 2 THEN '超级用户'
        WHEN 3 THEN '普通用户'
        ELSE '未知'
    END AS user_type_name,
    COUNT(*) as count
FROM users
GROUP BY user_type
ORDER BY user_type;
```

## ⚠️ 注意事项

1. **管理员账号保护**: 不能创建以 `admin` 为前缀的用户名
2. **批量导入限制**: 单次最多导入 1000 条记录
3. **用户类型限制**: 批量导入只能创建 super 和 common 用户，不能导入管理员
4. **默认值**: 如果不指定 user_type，默认为 3（普通用户）

## 📊 当前系统状态

运行以下命令查看当前用户状态：

```bash
mysql -h 127.0.0.1 -u root -p material_kb -e "SELECT id, username, role, user_type, status FROM users;"
```

示例输出：
```
+----+----------+-------+-----------+--------+
| id | username | role  | user_type | status |
+----+----------+-------+-----------+--------+
|  1 | admin    | admin |         1 | active |
|  2 | testuser | user  |         3 | active |
+----+----------+-------+-----------+--------+
```

## 🔄 版本历史

- **v1.0** (2026-01-31): 初始版本，添加 user_type 字段支持三级用户系统
