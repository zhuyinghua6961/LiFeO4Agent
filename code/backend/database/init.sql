-- 用户认证系统数据库初始化脚本
-- 数据库: material_kb
-- 字符集: utf8mb4

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS material_kb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE material_kb;

-- ==================== 用户表 ====================
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '加密后的密码',
    role ENUM('user', 'admin') NOT NULL DEFAULT 'user' COMMENT '角色',
    status ENUM('active', 'disabled') NOT NULL DEFAULT 'active' COMMENT '账号状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_username (username),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ==================== 对话会话表 ====================
DROP TABLE IF EXISTS conversations;
CREATE TABLE conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    title VARCHAR(255) COMMENT '对话标题(首条提问)',
    file_path VARCHAR(500) COMMENT '对话文件路径',
    message_count INT DEFAULT 0 COMMENT '消息数量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后消息时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话会话表';

-- ==================== 预设管理员账号 ====================
-- 密码: admin123 (bcrypt加密)
INSERT INTO users (username, password, role, status) VALUES
('admin', '$2b$12$/Oe84kDOlaVaeW..kk3NheqgUoTpBW5A2qxFrlH5ie3hGYEOUFZnO', 'admin', 'active');

-- ==================== 验证管理员账号 ====================
SELECT id, username, role, status, created_at FROM users WHERE username = 'admin';
