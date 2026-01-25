#!/bin/bash
# 启动 Marker 服务（带自动重启）和批处理

MARKER_DIR="/mnt/fast18/zhu/LiFeO4Agent/marker_service"

echo "=========================================="
echo "启动 Marker 服务（带自动重启监控）"
echo "=========================================="

cd "$MARKER_DIR" || exit 1

# 检查是否已经在运行
if pgrep -f "auto_restart_marker.sh" > /dev/null; then
    echo "⚠️  自动重启脚本已在运行"
    echo "如需重启，请先运行: pkill -f auto_restart_marker.sh"
    exit 1
fi

# 启动自动重启监控（后台运行）
echo "🚀 启动自动重启监控..."
nohup bash auto_restart_marker.sh > auto_restart.log 2>&1 &
AUTO_RESTART_PID=$!

echo "✅ 自动重启监控已启动 (PID: $AUTO_RESTART_PID)"
echo ""
echo "监控日志: tail -f $MARKER_DIR/auto_restart.log"
echo "Marker 日志: tail -f $MARKER_DIR/marker.log"
echo ""
echo "停止监控: pkill -f auto_restart_marker.sh"
echo "=========================================="

# 等待服务启动
echo "⏳ 等待 Marker 服务启动..."
sleep 15

# 检查服务是否启动成功
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "✅ Marker 服务已启动"
    echo ""
    echo "现在可以运行批处理脚本:"
    echo "  cd batch_process_pdf"
    echo "  conda run -n marker python batch_process_pdfs.py"
else
    echo "❌ Marker 服务启动失败，请检查日志"
    exit 1
fi
