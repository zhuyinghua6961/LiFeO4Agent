#!/bin/bash
#
# vLLM 服务启动脚本
# 用于启动 Qwen2.5-1.5B-Instruct 模型服务
# 端口: 8003 (用于关键词提取)
#

# 设置工作目录
WORK_DIR="/mnt/fast18/zhu/LiFeO4Agent"
cd "$WORK_DIR" || exit 1

# 日志文件
LOG_FILE="$WORK_DIR/qwen2.5B/vllm.log"
PID_FILE="$WORK_DIR/qwen2.5B/vllm.pid"

# 模型配置
MODEL_NAME="Qwen/Qwen2.5-1.5B-Instruct"
PORT=8003
MAX_MODEL_LEN=4096
GPU_MEMORY_UTIL=0.2

# Hugging Face 镜像站配置
export HF_ENDPOINT="https://hf-mirror.com"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  vLLM 服务启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否已经运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}警告: vLLM 服务已在运行 (PID: $OLD_PID)${NC}"
        echo -e "${YELLOW}如需重启，请先运行: ./qwen2.5B/stop_vllm.sh${NC}"
        exit 1
    else
        echo -e "${YELLOW}清理旧的 PID 文件...${NC}"
        rm -f "$PID_FILE"
    fi
fi

# 检查端口是否被占用
if lsof -i :$PORT > /dev/null 2>&1; then
    echo -e "${RED}错误: 端口 $PORT 已被占用${NC}"
    echo "占用端口的进程:"
    lsof -i :$PORT
    exit 1
fi

# 显示配置信息
echo "配置信息:"
echo "  模型: $MODEL_NAME"
echo "  端口: $PORT"
echo "  最大序列长度: $MAX_MODEL_LEN"
echo "  GPU 显存利用率: $GPU_MEMORY_UTIL"
echo "  HF 镜像站: $HF_ENDPOINT"
echo "  日志文件: $LOG_FILE"
echo ""

# 启动服务
echo -e "${GREEN}正在启动 vLLM 服务...${NC}"

nohup conda run -n vllm python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_NAME" \
    --port $PORT \
    --max-model-len $MAX_MODEL_LEN \
    --gpu-memory-utilization $GPU_MEMORY_UTIL \
    > "$LOG_FILE" 2>&1 &

# 保存 PID
PID=$!
echo $PID > "$PID_FILE"

echo -e "${GREEN}✓ vLLM 服务已启动${NC}"
echo "  进程 ID: $PID"
echo "  PID 文件: $PID_FILE"
echo ""

# 等待服务启动
echo "等待服务启动..."
sleep 5

# 检查进程是否还在运行
if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${RED}✗ 服务启动失败，进程已退出${NC}"
    echo "请查看日志: tail -f $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi

# 等待 API 可用
echo "等待 API 就绪..."
MAX_WAIT=60
WAIT_COUNT=0

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s http://localhost:$PORT/v1/models > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API 已就绪${NC}"
        break
    fi
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
    echo -n "."
done
echo ""

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}警告: API 启动超时 (${MAX_WAIT}秒)${NC}"
    echo "服务可能仍在初始化，请稍后检查"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  vLLM 服务启动完成${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "常用命令:"
echo "  查看日志: tail -f $LOG_FILE"
echo "  检查状态: curl http://localhost:$PORT/v1/models"
echo "  停止服务: ./qwen2.5B/stop_vllm.sh"
echo "  查看进程: ps -p $PID"
echo ""
