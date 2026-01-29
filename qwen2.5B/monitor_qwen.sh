#!/bin/bash
#
# Qwen 服务监控脚本
# 监控 vLLM 服务的运行状态、内存使用和请求处理
#

# 配置
PORT=8003
LOG_FILE="qwen2.5B/monitor.log"
CHECK_INTERVAL=60  # 检查间隔（秒）

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查服务是否运行
check_service() {
    if curl -s http://localhost:$PORT/v1/models > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 获取进程信息
get_process_info() {
    ps aux | grep "vllm.entrypoints.openai.api_server" | grep -v grep | grep -v conda
}

# 获取内存使用
get_memory_usage() {
    local pid=$1
    if [ -n "$pid" ]; then
        ps -p $pid -o rss= 2>/dev/null | awk '{printf "%.2f", $1/1024/1024}'
    else
        echo "0"
    fi
}

# 获取GPU内存
get_gpu_memory() {
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1
}

# 主监控循环
monitor() {
    log "========================================="
    log "Qwen 服务监控启动"
    log "端口: $PORT"
    log "检查间隔: ${CHECK_INTERVAL}秒"
    log "========================================="
    
    while true; do
        # 检查服务状态
        if check_service; then
            # 服务正常
            process_info=$(get_process_info)
            
            if [ -n "$process_info" ]; then
                pid=$(echo "$process_info" | awk '{print $2}')
                cpu=$(echo "$process_info" | awk '{print $3}')
                mem_pct=$(echo "$process_info" | awk '{print $4}')
                mem_gb=$(get_memory_usage $pid)
                
                # 获取GPU内存
                gpu_info=$(get_gpu_memory)
                gpu_used=$(echo "$gpu_info" | cut -d',' -f1 | tr -d ' ')
                gpu_total=$(echo "$gpu_info" | cut -d',' -f2 | tr -d ' ')
                
                # 计算运行时间
                etime=$(ps -p $pid -o etime= 2>/dev/null | tr -d ' ')
                
                echo -e "${GREEN}✓${NC} Service: HEALTHY | PID: $pid | CPU: ${cpu}% | MEM: ${mem_gb}GB (${mem_pct}%) | GPU: ${gpu_used}/${gpu_total}MB | Uptime: $etime"
                log "✓ Service HEALTHY - PID:$pid CPU:${cpu}% MEM:${mem_gb}GB GPU:${gpu_used}/${gpu_total}MB Uptime:$etime"
                
                # 检查内存警告
                if (( $(echo "$mem_gb > 2.0" | bc -l) )); then
                    echo -e "${YELLOW}⚠️  Warning: High memory usage (${mem_gb}GB)${NC}"
                    log "⚠️  WARNING: High memory usage ${mem_gb}GB"
                fi
                
                # 检查GPU内存警告
                if [ -n "$gpu_used" ] && [ -n "$gpu_total" ]; then
                    gpu_pct=$(echo "scale=2; $gpu_used * 100 / $gpu_total" | bc)
                    if (( $(echo "$gpu_pct > 80" | bc -l) )); then
                        echo -e "${YELLOW}⚠️  Warning: High GPU memory usage (${gpu_pct}%)${NC}"
                        log "⚠️  WARNING: High GPU memory usage ${gpu_pct}%"
                    fi
                fi
            else
                echo -e "${YELLOW}⚠️  Service API responding but process not found${NC}"
                log "⚠️  Service API responding but process not found"
            fi
        else
            # 服务不可用
            echo -e "${RED}✗${NC} Service: DOWN"
            log "✗ Service DOWN"
            
            # 检查进程是否存在
            process_info=$(get_process_info)
            if [ -n "$process_info" ]; then
                echo -e "${YELLOW}  Process exists but API not responding${NC}"
                log "  Process exists but API not responding"
            else
                echo -e "${RED}  Process not found${NC}"
                log "  Process not found"
            fi
        fi
        
        sleep $CHECK_INTERVAL
    done
}

# 单次检查模式
check_once() {
    echo "========================================="
    echo "  Qwen 服务状态检查"
    echo "========================================="
    echo ""
    
    if check_service; then
        echo -e "${GREEN}✓ Service is HEALTHY${NC}"
        
        process_info=$(get_process_info)
        if [ -n "$process_info" ]; then
            echo ""
            echo "Process Information:"
            echo "$process_info" | awk '{printf "  PID: %s\n  CPU: %s%%\n  MEM: %s%%\n  Command: %s\n", $2, $3, $4, substr($0, index($0,$11))}'
            
            pid=$(echo "$process_info" | awk '{print $2}')
            mem_gb=$(get_memory_usage $pid)
            echo "  Memory: ${mem_gb}GB"
            
            gpu_info=$(get_gpu_memory)
            if [ -n "$gpu_info" ]; then
                echo "  GPU Memory: $gpu_info MB"
            fi
        fi
    else
        echo -e "${RED}✗ Service is DOWN${NC}"
        exit 1
    fi
    
    echo ""
    echo "========================================="
}

# 解析命令行参数
case "${1:-monitor}" in
    monitor)
        monitor
        ;;
    check)
        check_once
        ;;
    *)
        echo "Usage: $0 {monitor|check}"
        echo "  monitor - Continuous monitoring (default)"
        echo "  check   - Single status check"
        exit 1
        ;;
esac
