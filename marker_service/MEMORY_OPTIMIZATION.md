# Marker 服务内存优化说明

## 🔧 已实施的优化措施

### 1. **服务端优化 (server.py)**

#### ✅ 自动重启机制
- **处理数限制**: 处理 50 个 PDF 后自动重启
- **内存阈值**: 内存使用超过 8GB 时自动重启
- **运行时间限制**: 运行超过 10 小时自动重启
- **触发方式**: 通过 `os._exit(1)` 退出，由 `auto_restart_marker.sh` 自动重启

#### ✅ 强制内存清理
每次转换后执行：
```python
def cleanup_memory():
    gc.collect()                    # Python 垃圾回收
    torch.cuda.empty_cache()        # 清理 GPU 缓存
    torch.cuda.synchronize()        # 同步 GPU 操作
```

#### ✅ 单线程模式
- 从 `threaded=True` 改为 `threaded=False`
- 避免线程泄露和线程池累积
- 使用 `werkzeug.serving.run_simple` 替代 `app.run()`

#### ✅ 对象生命周期管理
- 每次转换后删除 `rendered` 对象
- 立即调用 `gc.collect()` 强制回收
- 在 `finally` 块中确保临时文件删除

#### ✅ 内存监控
- 使用 `psutil` 实时监控内存使用
- 在 `/health` 接口返回内存状态
- 记录每次转换的内存使用情况

### 2. **批处理脚本优化 (batch_process_pdfs.py)**

#### ✅ Session 连接池管理
```python
adapter = requests.adapters.HTTPAdapter(
    pool_connections=1,
    pool_maxsize=1,
    max_retries=0
)
```
- 限制连接池大小为 1
- 避免连接泄露

#### ✅ 显式资源释放
```python
def __del__(self):
    if hasattr(self, 'session'):
        self.session.close()
```
- 在析构函数中关闭 session
- 每个 PDF 处理完后删除 client 对象

#### ✅ 定期垃圾回收
- 每处理 10 个 PDF 执行一次 `gc.collect()`
- 处理完成后清理 results 列表

## 📊 监控指标

### 健康检查接口
```bash
curl http://localhost:8002/health
```

返回信息：
```json
{
  "status": "healthy",
  "conversion_count": 25,
  "memory_usage_gb": 3.45,
  "uptime_hours": 2.3,
  "timestamp": "2026-01-26T15:30:00"
}
```

### 关键指标
- `conversion_count`: 已处理的 PDF 数量
- `memory_usage_gb`: 当前内存使用（GB）
- `uptime_hours`: 服务运行时间（小时）

## 🚨 重启触发条件

服务会在以下情况自动退出（由监控脚本重启）：

1. **处理数达到上限**: `conversion_count >= 50`
2. **内存超过阈值**: `memory_usage > 8.0 GB`
3. **运行时间过长**: `uptime > 10 hours`

## 🔍 故障排查

### 如果服务频繁重启

1. **检查内存使用**
```bash
# 查看进程内存
ps aux | grep "python.*server.py"

# 查看系统内存
free -h
```

2. **查看重启日志**
```bash
tail -f marker_service/auto_restart.log
```

3. **查看服务日志**
```bash
tail -f marker_service/marker.log
```

### 如果内存仍然泄露

1. **降低处理数限制**
   - 修改 `MAX_CONVERSIONS = 50` 为更小的值（如 20）

2. **降低内存阈值**
   - 修改 `MEMORY_THRESHOLD_GB = 8.0` 为更小的值（如 6.0）

3. **缩短运行时间**
   - 修改运行时间限制为更短（如 5 小时）

## 📝 配置参数

在 `server.py` 中可调整：

```python
MAX_CONVERSIONS = 50          # 最大处理数
MEMORY_THRESHOLD_GB = 8.0     # 内存阈值（GB）
uptime_limit = 10             # 运行时间限制（小时）
```

## 🎯 预期效果

- **服务稳定性**: 不再因内存耗尽而崩溃
- **自动恢复**: 达到限制后自动重启，无需人工干预
- **资源可控**: 内存使用保持在合理范围内
- **长期运行**: 可以持续处理大量 PDF 而不死机

## ⚠️ 注意事项

1. **首次启动**: 需要安装 `psutil`
   ```bash
   conda run -n marker pip install psutil
   ```

2. **监控脚本**: 确保 `auto_restart_marker.sh` 正在运行
   ```bash
   ps aux | grep auto_restart_marker.sh
   ```

3. **GPU 内存**: 如果使用 GPU，确保 CUDA 驱动正常

4. **批处理**: 大批量处理时建议分批进行，每批不超过 100 个 PDF
