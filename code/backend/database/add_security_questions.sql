-- 添加安全问题字段到 users 表
-- 数据库: material_kb

USE material_kb;

-- 如果字段已存在，先删除
ALTER TABLE users DROP COLUMN IF EXISTS password_reset_expires;
ALTER TABLE users DROP COLUMN IF EXISTS password_reset_token;
ALTER TABLE users DROP COLUMN IF EXISTS security_questions;

-- 添加字段
ALTER TABLE users ADD COLUMN security_questions TEXT COMMENT '安全问题设置，格式: [{"question":"问题1","answer":"答案1"}, ...]';
ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(64) DEFAULT NULL COMMENT '密码重置token';
ALTER TABLE users ADD COLUMN password_reset_expires TIMESTAMP DEFAULT NULL COMMENT 'token过期时间';

-- 为管理员用户设置默认安全问题
UPDATE users SET security_questions = '[{"question":"管理员默认问题： admin 是什么？","answer":"admin"}]' WHERE username = 'admin';

-- 验证字段已添加
DESCRIBE users;

-- 验证管理员安全问题
SELECT id, username, security_questions FROM users WHERE username = 'admin';
