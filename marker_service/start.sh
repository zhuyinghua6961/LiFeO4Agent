#!/bin/bash
# Marker服务启动脚本

echo "================================"
echo "Marker PDF服务启动脚本"
echo "================================"

# 激活conda环境（如果使用conda）
if command -v conda &> /dev/null; then
    echo "激活conda环境: marker"
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate marker
fi

# 检查Python版本
echo ""
echo "Python版本:"
python --version

# 检查GPU
echo ""
echo "GPU检查:"
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

# 启动服务
echo ""
echo "================================"
echo "启动Marker服务..."
echo "端口: 8002"
echo "================================"
echo ""

python server.py
