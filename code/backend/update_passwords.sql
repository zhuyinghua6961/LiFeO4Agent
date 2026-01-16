-- 更新用户密码为AES加密格式
-- 执行前请确保已安装 pycryptodome

UPDATE users SET password = 'UbqLaKrUVMRVtc94ZzJrRl/27V+xbUPU+yDY6MoyEE0=' WHERE username = 'admin';
UPDATE users SET password = 'FyUhVhTXxHZATktfbahWqgwg1pG/NnwO6iYZu7qrsQ4=' WHERE username = 'testuser';
UPDATE users SET password = 'leXNi3c8hUsPKqeJ6jJD5yppBkcbszYRe8mZpAk4LXk=' WHERE username = 'zyh';
