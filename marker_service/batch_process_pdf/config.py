"""
批处理配置文件
"""

import os

# Marker服务地址
MARKER_SERVICE_URL = 'http://localhost:8002'

# PDF输入目录（自动展开 ~ 和相对路径）
PDF_INPUT_DIR = os.path.expanduser('/mnt/fast18/zhu/agentCode/papers')

# Markdown输出目录（自动展开相对路径）
MARKDOWN_OUTPUT_DIR = os.path.abspath('../outputs')

# 最大并发数
MAX_WORKERS = 10

# 请求超时时间（秒）
REQUEST_TIMEOUT = 300

# 默认语言
DEFAULT_LANGS = 'en,zh'
