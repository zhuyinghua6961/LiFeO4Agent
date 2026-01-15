#!/bin/bash
# 磷酸铁锂知识图谱 AI 启动脚本

cd "$(dirname "$0")"

echo "============================================================"
echo "🚀 启动磷酸铁锂知识图谱 AI"
echo "============================================================"

# 停止现有服务
pkill -f "python.*backend/main.py" 2>/dev/null
sleep 2

# 确保日志目录存在
mkdir -p logs

# 启动后端
echo "📦 启动后端服务..."
nohup python code/backend/main.py > logs/backend.log 2>&1 &
BACKEND_PID=$!

echo "   后端 PID: $BACKEND_PID"
echo "   日志位置: logs/backend.log"

# 等待后端启动
sleep 3

# 检查后端是否启动成功
if curl -s http://localhost:8000/api/kb_info > /dev/null 2>&1; then
    echo "✅ 后端启动成功"
else
    echo "❌ 后端启动失败，请检查 logs/backend.log"
fi

echo ""
echo "============================================================"
echo "✅ 启动完成!"
echo "============================================================"
echo "📝 使用说明:"
echo "   - 后端API: http://localhost:8000"
echo "   - 前端Vue: 请在 code/frontend-vue 目录运行 npm run dev"
echo "   - 日志文件: logs/backend.log"
echo ""
