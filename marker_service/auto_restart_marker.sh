#!/bin/bash
# Marker 服务自动重启脚本
# 监控 Marker 服务，如果崩溃则自动重启

# 配置
MARKER_PORT=8002
MARKER_DIR="/mnt/fast18/zhu/LiFeO4Agent/marker_service"
LOG_FILE="$MARKER_DIR/auto_restart.log"
CONDA_ENV="marker"
CHECK_INTERVAL=30  # 检查间隔（秒）

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查服务是否运行
check_service() {
    curl -s http://localhost:$MARKER_PORT/health > /dev/null 2>&1
    return $?
}

# 启动服务
start_service() {
    log "🚀 启动 Marker 服务..."
    
    # 切换到 marker 目录
    cd "$MARKER_DIR" || exit 1
    
    # 使用 conda 环境启动服务
    nohup conda run -n $CONDA_ENV python server.py > marker.log 2>&1 &
    
    # 等待服务启动
    sleep 10
    
    # 验证服务是否启动成功
    if check_service; then
        log "✅ Marker 服务启动成功"
        return 0
    else
        log "❌ Marker 服务启动失败"
        return 1
    fi
}

# 停止服务
stop_service() {
    log "🛑 停止 Marker 服务..."
    
    # 查找并杀死进程
    pkill -f "python server.py" || true
    
    sleep 2
    log "✅ Marker 服务已停止"
}

# 主循环
main() {
    log "=========================================="
    log "Marker 自动重启监控脚本启动"
    log "端口: $MARKER_PORT"
    log "检查间隔: ${CHECK_INTERVAL}秒"
    log "=========================================="
    
    # 初始启动
    if ! check_service; then
        log "⚠️  服务未运行，首次启动..."
        start_service
    else
        log "✅ 服务已在运行"
    fi
    
    # 监控循环
    restart_count=0
    
    while true; do
        sleep $CHECK_INTERVAL
        
        if ! check_service; then
            log "❌ 检测到服务崩溃！"
            restart_count=$((restart_count + 1))
            log "📊 重启次数: $restart_count"
            
            # 停止旧进程
            stop_service
            
            # 等待一段时间
            sleep 5
            
            # 重启服务
            if start_service; then
                log "✅ 服务重启成功（第 $restart_count 次）"
            else
                log "❌ 服务重启失败（第 $restart_count 次）"
                log "⏸️  等待 60 秒后重试..."
                sleep 60
            fi
        else
            # 服务正常运行
            if [ $((RANDOM % 20)) -eq 0 ]; then
                log "✓ 服务运行正常（已重启 $restart_count 次）"
            fi
        fi
    done
}

# 捕获退出信号
trap 'log "收到退出信号，停止监控..."; stop_service; exit 0' SIGINT SIGTERM

# 运行主程序
main
