#!/bin/bash
#
# vLLM 服务停止脚本
#

# 设置工作目录
WORK_DIR="/mnt/fast18/zhu/LiFeO4Agent"
cd "$WORK_DIR" || exit 1

# PID 文件
PID_FILE="$WORK_DIR/qwen2.5B/vllm.pid"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  vLLM 服务停止脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查 PID 文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}警告: 未找到 PID 文件${NC}"
    echo "尝试查找运行中的 vLLM 进程..."
    
    # 查找 vLLM 进程
    PIDS=$(ps aux | grep "vllm.entrypoints.openai.api_server" | grep -v grep | awk '{print $2}')
    
    if [ -z "$PIDS" ]; then
        echo -e "${YELLOW}未找到运行中的 vLLM 进程${NC}"
        exit 0
    else
        echo "找到以下 vLLM 进程:"
        ps aux | grep "vllm.entrypoints.openai.api_server" | grep -v grep
        echo ""
        
        for PID in $PIDS; do
            echo -e "${YELLOW}停止进程 $PID...${NC}"
            kill $PID
            sleep 2
            
            # 检查是否还在运行
            if ps -p $PID > /dev/null 2>&1; then
                echo -e "${YELLOW}进程未响应，强制终止...${NC}"
                kill -9 $PID
            fi
        done
        
        echo -e "${GREEN}✓ 所有 vLLM 进程已停止${NC}"
        exit 0
    fi
fi

# 读取 PID
PID=$(cat "$PID_FILE")

# 检查进程是否存在
if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${YELLOW}进程 $PID 不存在${NC}"
    rm -f "$PID_FILE"
    echo -e "${GREEN}✓ 清理完成${NC}"
    exit 0
fi

# 显示进程信息
echo "进程信息:"
ps -p $PID -o pid,ppid,cmd,etime
echo ""

# 停止进程
echo -e "${YELLOW}正在停止 vLLM 服务 (PID: $PID)...${NC}"
kill $PID

# 等待进程结束
echo "等待进程结束..."
WAIT_COUNT=0
MAX_WAIT=10

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 进程已正常结束${NC}"
        rm -f "$PID_FILE"
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  vLLM 服务已停止${NC}"
        echo -e "${GREEN}========================================${NC}"
        exit 0
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    echo -n "."
done
echo ""

# 如果进程还在运行，强制终止
echo -e "${YELLOW}进程未响应，强制终止...${NC}"
kill -9 $PID
sleep 1

if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 进程已强制终止${NC}"
    rm -f "$PID_FILE"
else
    echo -e "${RED}✗ 无法终止进程${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  vLLM 服务已停止${NC}"
echo -e "${GREEN}========================================${NC}"
