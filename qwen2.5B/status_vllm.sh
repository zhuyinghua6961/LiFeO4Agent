#!/bin/bash
#
# vLLM 服务状态检查脚本
#

# 设置工作目录
WORK_DIR="/mnt/fast18/zhu/LiFeO4Agent"
cd "$WORK_DIR" || exit 1

# PID 文件
PID_FILE="$WORK_DIR/qwen2.5B/vllm.pid"
LOG_FILE="$WORK_DIR/qwen2.5B/vllm.log"
PORT=8003

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  vLLM 服务状态检查${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查 PID 文件
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "PID 文件: $PID_FILE"
    echo "进程 ID: $PID"
    echo ""
    
    # 检查进程是否运行
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 进程正在运行${NC}"
        echo ""
        echo "进程详情:"
        ps -p $PID -o pid,ppid,cmd,etime,%cpu,%mem
        echo ""
    else
        echo -e "${RED}✗ 进程不存在 (PID 文件过期)${NC}"
        echo ""
    fi
else
    echo -e "${YELLOW}未找到 PID 文件${NC}"
    echo ""
fi

# 检查端口
echo "端口检查 (端口 $PORT):"
if lsof -i :$PORT > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 端口 $PORT 正在监听${NC}"
    echo ""
    lsof -i :$PORT
    echo ""
else
    echo -e "${RED}✗ 端口 $PORT 未被监听${NC}"
    echo ""
fi

# 检查 API
echo "API 健康检查:"
if curl -s http://localhost:$PORT/v1/models > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API 可访问${NC}"
    echo ""
    echo "可用模型:"
    curl -s http://localhost:$PORT/v1/models | python -m json.tool 2>/dev/null || echo "无法解析响应"
    echo ""
else
    echo -e "${RED}✗ API 不可访问${NC}"
    echo ""
fi

# 显示最近的日志
if [ -f "$LOG_FILE" ]; then
    echo "最近的日志 (最后 10 行):"
    echo "----------------------------------------"
    tail -n 10 "$LOG_FILE"
    echo "----------------------------------------"
    echo ""
    echo "完整日志: tail -f $LOG_FILE"
else
    echo -e "${YELLOW}未找到日志文件${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
