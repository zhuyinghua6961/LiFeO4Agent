#!/bin/bash
#
# 关键词提取进度检查脚本
#

echo "========================================="
echo "  关键词提取进度检查"
echo "========================================="
echo ""

# 检查批处理进程
echo "1. 批处理进程状态:"
if ps aux | grep "batch_extract_keywords" | grep -v grep > /dev/null; then
    echo "   ✓ 批处理进程正在运行"
    ps aux | grep "batch_extract_keywords" | grep -v grep | awk '{print "   PID: " $2 " | CPU: " $3 "% | MEM: " $4 "%"}'
else
    echo "   ✗ 批处理进程未运行"
fi
echo ""

# 检查 Qwen 服务
echo "2. Qwen 服务状态:"
if curl -s http://localhost:8003/v1/models > /dev/null 2>&1; then
    echo "   ✓ Qwen 服务正常"
else
    echo "   ✗ Qwen 服务异常"
fi
echo ""

# 检查进度
echo "3. 处理进度:"
total_files=6252
if [ -f rebuild_vector_db/keyword_extraction_progress.txt ]; then
    processed=$(wc -l < rebuild_vector_db/keyword_extraction_progress.txt)
    remaining=$((total_files - processed))
    percentage=$(echo "scale=2; $processed * 100 / $total_files" | bc)
    echo "   已处理: $processed / $total_files 文件 (${percentage}%)"
    echo "   剩余: $remaining 文件"
    
    # 估算剩余时间（假设每个文件平均 1.5 秒）
    if [ $processed -gt 10 ]; then
        avg_time=1.5
        remaining_time=$(echo "scale=0; $remaining * $avg_time / 60" | bc)
        echo "   预计剩余时间: ~${remaining_time} 分钟"
    fi
else
    echo "   进度文件不存在"
fi
echo ""

# 检查输出目录
echo "4. 输出文件:"
output_dir="/mnt/fast18/zhu/LiFeO4Agent/rebuild_vector_db/chunks_data_with_keywords"
if [ -d "$output_dir" ]; then
    output_count=$(ls "$output_dir"/*.json 2>/dev/null | wc -l)
    echo "   输出目录: $output_dir"
    echo "   已生成文件: $output_count"
else
    echo "   输出目录不存在"
fi
echo ""

# 检查最近的日志
echo "5. 最近的日志 (最后 5 行):"
if [ -f rebuild_vector_db/keyword_extraction.log ]; then
    tail -5 rebuild_vector_db/keyword_extraction.log | sed 's/^/   /'
else
    echo "   日志文件不存在"
fi
echo ""

echo "========================================="
echo "提示: 使用 'tail -f rebuild_vector_db/keyword_extraction.log' 查看实时日志"
echo "提示: 使用 'tail -f qwen2.5B/monitor.log' 查看 Qwen 服务监控日志"
echo "========================================="
