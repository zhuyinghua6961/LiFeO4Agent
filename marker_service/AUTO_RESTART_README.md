# Marker 服务自动重启功能

## 功能说明

当 Marker 服务在处理大量 PDF 时崩溃，自动重启脚本会：
1. 每 30 秒检查一次服务健康状态
2. 检测到服务崩溃时自动重启
3. 使用 `marker` conda 环境重启服务
4. 记录所有重启事件到日志

批处理脚本会：
1. 检测到服务不可用时等待服务恢复（最多 5 分钟）
2. 服务恢复后自动重试失败的 PDF
3. 跳过已处理的文件（默认开启）

## 快速开始

### 方法 1：一键启动（推荐）

```bash
cd marker_service
bash start_with_auto_restart.sh
```

然后在另一个终端运行批处理：

```bash
cd marker_service/batch_process_pdf
conda run -n marker python batch_process_pdfs.py
```

### 方法 2：手动启动

#### 1. 启动自动重启监控

```bash
cd marker_service
nohup bash auto_restart_marker.sh > auto_restart.log 2>&1 &
```

#### 2. 运行批处理（会自动跳过已处理的文件）

```bash
cd batch_process_pdf
conda run -n marker python batch_process_pdfs.py
```

#### 3. 强制重新处理所有文件

```bash
conda run -n marker python batch_process_pdfs.py --force
```

## 监控和日志

### 查看自动重启日志

```bash
tail -f marker_service/auto_restart.log
```

### 查看 Marker 服务日志

```bash
tail -f marker_service/marker.log
```

### 查看批处理日志

```bash
tail -f marker_service/batch_process_pdf/process.log
```

### 查看批处理报告

```bash
cat marker_service/outputs/batch_processing_report.json
```

## 停止服务

### 停止自动重启监控

```bash
pkill -f auto_restart_marker.sh
```

### 停止 Marker 服务

```bash
pkill -f "python server.py"
```

### 停止批处理

```bash
# 按 Ctrl+C 或
pkill -f batch_process_pdfs.py
```

## 配置说明

### 自动重启配置

编辑 `auto_restart_marker.sh`：

```bash
MARKER_PORT=8002          # Marker 服务端口
CHECK_INTERVAL=30         # 检查间隔（秒）
CONDA_ENV="marker"        # Conda 环境名称
```

### 批处理配置

编辑 `batch_process_pdf/config.py`：

```python
MARKER_SERVICE_URL = 'http://localhost:8002'
PDF_INPUT_DIR = '/mnt/fast18/zhu/agentCode/papers'
MARKDOWN_OUTPUT_DIR = './outputs'
MAX_WORKERS = 10
REQUEST_TIMEOUT = 300
```

## 命令行参数

### batch_process_pdfs.py

```bash
# 查看帮助
python batch_process_pdfs.py --help

# 自定义 PDF 目录
python batch_process_pdfs.py --pdf-dir /path/to/pdfs

# 自定义输出目录
python batch_process_pdfs.py --output-dir /path/to/output

# 强制重新处理所有文件
python batch_process_pdfs.py --force

# 自定义 Marker 服务地址
python batch_process_pdfs.py --marker-url http://localhost:8002
```

## 故障排查

### 服务无法启动

1. 检查端口是否被占用：
   ```bash
   lsof -i :8002
   ```

2. 检查 conda 环境：
   ```bash
   conda env list
   conda activate marker
   ```

3. 手动启动测试：
   ```bash
   cd marker_service
   conda run -n marker python server.py
   ```

### 批处理失败率高

1. 检查服务日志：
   ```bash
   tail -100 marker_service/marker.log
   ```

2. 检查是否是特定 PDF 导致崩溃：
   ```bash
   grep "开始处理PDF" marker_service/marker.log | tail -5
   ```

3. 增加重试次数（修改 `batch_process_pdfs.py` 中的 `max_retries`）

### 自动重启不工作

1. 检查监控脚本是否运行：
   ```bash
   ps aux | grep auto_restart_marker.sh
   ```

2. 检查日志：
   ```bash
   tail -50 marker_service/auto_restart.log
   ```

3. 手动测试健康检查：
   ```bash
   curl http://localhost:8002/health
   ```

## 性能优化建议

1. **调整检查间隔**：如果服务很稳定，可以增加 `CHECK_INTERVAL` 到 60 秒
2. **调整等待时间**：修改 `wait_for_service` 的 `max_wait` 参数
3. **批处理并发**：目前是串行处理，可以根据需要调整（但要注意服务负载）

## 当前状态

- **总 PDF 数量**：6,254 个
- **已处理**：801 个
- **待处理**：5,453 个
- **成功率**：12.8%（首次运行，包含服务崩溃）

使用自动重启功能后，预期成功率会大幅提升。
