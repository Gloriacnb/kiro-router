# macOS 服务测试验证指南

本文档提供完整的测试流程，验证 macOS 后台运行功能是否正常工作。

## 前置条件

1. 已完成 Kiro Gateway 的全局安装
2. 已配置 `.env` 文件
3. 已运行 `install-macos-service.sh`

## 测试流程

### 1. 安装测试

验证服务安装是否成功：

```bash
cd macos-service
./install-macos-service.sh
```

**预期结果：**
- ✅ 显示 "Found kiro-gateway at: ..."
- ✅ 显示 "Found .env file in current directory" 或提示输入路径
- ✅ 显示 "Created LaunchAgents directory"
- ✅ 显示 "Created log directory"
- ✅ 显示 "Service loaded successfully!"
- ✅ 显示 "Service is running!"

**验证命令：**

```bash
# 检查服务是否已加载
launchctl list | grep com.github.kirowhat.gateway

# 检查 plist 文件是否存在
ls -la ~/Library/LaunchAgents/com.github.kirowhat.gateway.plist

# 检查日志目录是否存在
ls -la ~/Library/Logs/com.github.kirowhat.gateway/
```

### 2. 启动测试

验证服务启动功能：

```bash
./kiro-gateway-service.sh start
```

**预期结果：**
- ✅ 显示 "Starting Kiro Gateway Service"
- ✅ 显示 "Service started successfully!"
- ✅ 显示服务状态信息

### 3. 状态测试

验证状态查看功能：

```bash
./kiro-gateway-service.sh status
```

**预期结果：**
```
ℹ Service Status

  State: Running
  PID:   12345
  Memory: XX.X MB
  Health: ✓ OK (http://localhost:8000/health)
```

### 4. 健康检查测试

验证 API 端点是否正常响应：

```bash
# 测试健康检查端点
curl http://localhost:8000/health

# 预期响应：{"status":"ok"}
```

### 5. 停止测试

验证服务停止功能：

```bash
./kiro-gateway-service.sh stop
```

**预期结果：**
- ✅ 显示 "Stopping Kiro Gateway Service"
- ✅ 显示 "Service stopped successfully!"

**验证服务已停止：**

```bash
./kiro-gateway-service.sh status
# 预期显示：State: Not loaded 或 State: Not running

curl http://localhost:8000/health
# 预期：连接失败
```

### 6. 重启测试

验证服务重启功能：

```bash
./kiro-gateway-service.sh restart
```

**预期结果：**
- ✅ 显示 "Restarting Kiro Gateway Service"
- ✅ 显示 "Service restarted successfully!"
- ✅ 服务 PID 发生变化

### 7. 日志测试

验证日志功能：

```bash
# 查看所有日志
./kiro-gateway-service.sh logs

# 在另一个终端触发请求
curl http://localhost:8000/health

# 观察日志输出是否包含请求信息
```

**预期结果：**
- ✅ 显示 "Showing combined logs (Ctrl+C to exit)..."
- ✅ 显示应用启动日志
- ✅ 显示 HTTP 请求日志

**手动验证日志文件：**

```bash
# 查看 stdout 日志
cat ~/Library/Logs/com.github.kirowhat.gateway/stdout.log

# 查看 stderr 日志
cat ~/Library/Logs/com.github.kirowhat.gateway/stderr.log

# 实时查看日志
tail -f ~/Library/Logs/com.github.kirowhat.gateway/stdout.log
```

### 8. API 功能测试

验证代理网关功能是否正常：

```bash
# 测试模型列表端点
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer your-secret-key"

# 预期：返回可用模型列表
```

### 9. 开机自启测试

验证开机自动启动功能：

```bash
# 1. 确保服务正在运行
./kiro-gateway-service.sh status

# 2. 重启系统
# 重启后打开终端

# 3. 检查服务状态
./kiro-gateway-service.sh status

# 预期：显示 State: Running
```

**替代方法（无需重启）：**

```bash
# 1. 注销当前用户（不要重启）
# 2. 重新登录
# 3. 检查服务状态
./kiro-gateway-service.sh status
```

### 10. 崩溃恢复测试

验证进程崩溃时自动重启：

```bash
# 1. 获取服务 PID
./kiro-gateway-service.sh status

# 2. 杀死进程
kill -9 <PID>

# 3. 等待 5-10 秒

# 4. 检查服务状态
./kiro-gateway-service.sh status

# 预期：显示新的 PID（服务已自动重启）
```

### 11. 环境变量测试

验证环境变量是否正确传递：

```bash
# 1. 查看日志中的配置信息
./kiro-gateway-service.sh logs | grep -i "host\|port"

# 2. 或者在 .env 中设置特殊端口
echo "SERVER_PORT=9000" >> .env

# 3. 重启服务
./kiro-gateway-service.sh restart

# 4. 测试新端口
curl http://localhost:9000/health

# 5. 恢复原端口
# 编辑 .env 移除 SERVER_PORT 行，然后重启
```

### 12. 卸载测试

验证卸载功能：

```bash
./kiro-gateway-service.sh uninstall
```

**预期结果：**
- ✅ 显示 "Uninstalling Kiro Gateway Service"
- ✅ 询问是否删除日志
- ✅ 显示 "Uninstallation complete!"

**验证卸载成功：**

```bash
# 检查服务是否已卸载
launchctl list | grep com.github.kirowhat.gateway
# 预期：无输出

# 检查 plist 文件是否已删除
ls ~/Library/LaunchAgents/com.github.kirowhat.gateway.plist 2>&1
# 预期：No such file or directory
```

## 故障排查检查清单

如果测试失败，按顺序检查：

### 1. 检查 kiro-gateway 安装

```bash
which kiro-gateway
kiro-gateway --version
```

**问题：找不到命令**

解决方法：
```bash
cd /path/to/kiro-router
uv tool install . --global --reinstall
```

### 2. 检查 .env 配置

```bash
cat .env
```

**必要配置：**
- `PROXY_API_KEY`: 已设置
- `KIRO_CLI_DB_FILE` 或 `KIRO_CREDS_FILE` 或 `REFRESH_TOKEN`: 至少一个

### 3. 检查端口占用

```bash
lsof -i :8000
```

**问题：端口被占用**

解决方法：
- 停止占用端口的进程
- 或在 `.env` 中设置其他端口：`SERVER_PORT=9000`

### 4. 检查日志错误

```bash
cat ~/Library/Logs/com.github.kirowhat.gateway/stderr.log
```

**常见错误：**

- "No Kiro credentials configured": 检查 `.env` 配置
- "Address already in use": 端口被占用
- "Permission denied": 检查文件权限

### 5. 检查 launchd 加载状态

```bash
launchctl list | grep com.github.kirowhat.gateway
```

**问题：服务未加载**

解决方法：
```bash
launchctl load ~/Library/LaunchAgents/com.github.kirowhat.gateway.plist
```

### 6. 手动运行测试

```bash
# 手动运行以查看错误
kiro-gateway
```

观察是否有错误信息，修复后再安装服务。

## 测试结果记录

完成测试后，记录结果：

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 安装测试 | ⬜ 通过 / ❌ 失败 |  |
| 启动测试 | ⬜ 通过 / ❌ 失败 |  |
| 状态测试 | ⬜ 通过 / ❌ 失败 |  |
| 健康检查 | ⬜ 通过 / ❌ 失败 |  |
| 停止测试 | ⬜ 通过 / ❌ 失败 |  |
| 重启测试 | ⬜ 通过 / ❌ 失败 |  |
| 日志测试 | ⬜ 通过 / ❌ 失败 |  |
| API 功能 | ⬜ 通过 / ❌ 失败 |  |
| 开机自启 | ⬜ 通过 / ❌ 失败 |  |
| 崩溃恢复 | ⬜ 通过 / ❌ 失败 |  |
| 环境变量 | ⬜ 通过 / ❌ 失败 |  |
| 卸载测试 | ⬜ 通过 / ❌ 失败 |  |

## 性能基准

记录服务的资源使用情况：

```bash
# 启动服务后
./kiro-gateway-service.sh status

# 记录初始内存占用
```

**预期性能：**
- 内存占用: < 100 MB
- 启动时间: < 5 秒
- 响应时间: < 100ms（健康检查）

## 下一步

测试通过后：

1. ✅ 配置 IDE（Claude Code / Cursor / Cline）
2. ✅ 设置开机自启（已完成）
3. ✅ 开始使用 Kiro Gateway

## 获取帮助

如果遇到问题：

1. 查看 [README.md](README.md) 的故障排查章节
2. 检查日志文件
3. 访问 [GitHub Issues](https://github.com/jwadow/kiro-gateway/issues)
