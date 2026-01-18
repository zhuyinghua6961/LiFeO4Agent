#!/bin/bash
# ================================================================
# 磷酸铁锂Agent系统 - 服务器路径自动更新脚本
# 用途：一键修改所有硬编码路径，适配新服务器环境
# ================================================================

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 服务器路径配置
NEW_ROOT="/home/磷酸铁锂agent"
NEW_BGE_PATH="${NEW_ROOT}/bge-3/BGE"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}磷酸铁锂Agent - 路径更新脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}新的根路径:${NC} ${NEW_ROOT}"
echo -e "${YELLOW}BGE模型路径:${NC} ${NEW_BGE_PATH}"
echo ""

# 检查是否在正确的目录
if [ ! -f "main.py" ] || [ ! -f "web_app.py" ]; then
    echo -e "${RED}❌ 错误: 请在项目根目录下运行此脚本！${NC}"
    exit 1
fi

# 备份原文件
echo -e "${YELLOW}📦 备份原文件...${NC}"
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp main.py microscopic_expert.py community_expert.py vectorize_communities.py zy.py 直接导入.py "$BACKUP_DIR/" 2>/dev/null
echo -e "${GREEN}✅ 备份完成: $BACKUP_DIR/${NC}"
echo ""

# 修改BGE模型路径
echo -e "${YELLOW}🔧 修改BGE模型路径...${NC}"
files_to_update=(
    "main.py"
    "microscopic_expert.py"
    "community_expert.py"
    "vectorize_communities.py"
    "zy.py"
)

for file in "${files_to_update[@]}"; do
    if [ -f "$file" ]; then
        sed -i.bak "s|/Users/qychen/研究生/研一下/bge-3/BGE|${NEW_BGE_PATH}|g" "$file"
        rm -f "${file}.bak"  # 删除sed产生的备份文件
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (文件不存在)"
    fi
done
echo ""

# 修改直接导入脚本中的路径
echo -e "${YELLOW}🔧 修改直接导入脚本路径...${NC}"
if [ -f "直接导入.py" ]; then
    sed -i.bak "s|/Users/qychen/研究生/磷酸铁锂agent|${NEW_ROOT}|g" "直接导入.py"
    rm -f "直接导入.py.bak"
    echo -e "  ${GREEN}✓${NC} 直接导入.py"
else
    echo -e "  ${RED}✗${NC} 直接导入.py (文件不存在)"
fi
echo ""

# 检查config.env
echo -e "${YELLOW}📝 检查config.env配置...${NC}"
if [ -f "config.env" ]; then
    echo -e "  ${GREEN}✓${NC} config.env 存在"
    echo -e "  ${YELLOW}⚠️  请手动检查以下配置:${NC}"
    echo -e "     - NEO4J_URL (服务器上的Neo4j地址)"
    echo -e "     - NEO4J_USERNAME"
    echo -e "     - NEO4J_PASSWORD"
    echo -e "     - DEEPSEEK_API_KEY"
else
    echo -e "  ${RED}✗${NC} config.env 不存在，请创建！"
fi
echo ""

# 检查关键路径是否存在
echo -e "${YELLOW}🔍 检查关键路径...${NC}"
if [ -d "${NEW_BGE_PATH}" ]; then
    echo -e "  ${GREEN}✓${NC} BGE模型路径存在: ${NEW_BGE_PATH}"
else
    echo -e "  ${RED}✗${NC} BGE模型路径不存在: ${NEW_BGE_PATH}"
    echo -e "     ${YELLOW}请确保BGE模型已上传到服务器！${NC}"
fi

if [ -d "vector_database" ]; then
    echo -e "  ${GREEN}✓${NC} 向量数据库目录存在"
else
    echo -e "  ${YELLOW}⚠️${NC}  向量数据库目录不存在，可能需要重新导入数据"
fi

if [ -d "json" ]; then
    json_count=$(ls -1 json/*.json 2>/dev/null | wc -l)
    echo -e "  ${GREEN}✓${NC} json数据目录存在 (${json_count}个文件)"
else
    echo -e "  ${YELLOW}⚠️${NC}  json数据目录不存在"
fi
echo ""

# 完成
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 路径更新完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}📋 后续步骤:${NC}"
echo -e "  1. 编辑 config.env，修改Neo4j连接信息"
echo -e "  2. 确保BGE模型已上传到: ${NEW_BGE_PATH}"
echo -e "  3. 创建虚拟环境: python3.9 -m venv agent"
echo -e "  4. 激活环境: source agent/bin/activate"
echo -e "  5. 安装依赖: pip install -r requirements.txt"
echo -e "  6. (可选)导入向量数据: ./agent/bin/python 直接导入.py"
echo -e "  7. 启动服务: ./agent/bin/python web_app.py"
echo ""
echo -e "${GREEN}💡 提示:${NC} 如果需要恢复原文件，请查看备份目录: ${BACKUP_DIR}"

