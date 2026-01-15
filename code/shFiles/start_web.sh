#!/bin/bash
# 磷酸铁锂知识图谱问答系统 - Web服务启动脚本

echo "=========================================="
echo "🚀 启动磷酸铁锂知识图谱问答系统"
echo "=========================================="
echo ""

# 检查Python版本
python_version=$(python3 --version 2>&1)
echo "✓ Python版本: $python_version"

# 检查是否在虚拟环境中
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✓ 虚拟环境: $VIRTUAL_ENV"
else
    echo "⚠️  建议在虚拟环境中运行"
    echo "   如需激活: source agent/bin/activate"
fi

echo ""
echo "=========================================="
echo "📦 检查依赖..."
echo "=========================================="

# 检查关键依赖
dependencies=("flask" "neo4j" "langchain" "chromadb")
missing_deps=()

for dep in "${dependencies[@]}"; do
    if python3 -c "import $dep" 2>/dev/null; then
        echo "✓ $dep 已安装"
    else
        echo "✗ $dep 未安装"
        missing_deps+=("$dep")
    fi
done

if [ ${#missing_deps[@]} -ne 0 ]; then
    echo ""
    echo "❌ 缺少依赖，请先安装:"
    echo "   pip install -r requirements.txt"
    exit 1
fi

echo ""
echo "=========================================="
echo "🔧 检查配置..."
echo "=========================================="

# 检查配置文件
if [ ! -f "config.env" ]; then
    echo "❌ 配置文件 config.env 不存在"
    echo "   请复制 config.env.example 并配置"
    exit 1
else
    echo "✓ 配置文件存在"
fi

# 检查静态文件
if [ ! -f "static/index.html" ]; then
    echo "❌ 前端文件不存在"
    exit 1
else
    echo "✓ 前端文件存在"
fi

echo ""
echo "=========================================="
echo "🌐 启动Web服务..."
echo "=========================================="
echo ""

# 启动Flask应用
python3 web_app.py

