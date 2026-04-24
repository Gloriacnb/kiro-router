# Kiro Gateway macOS Service

Kiro Gateway 的 macOS 后台运行和开机自启服务。

## 快速开始

### 前置要求

确保已全局安装 `kiro-gateway` 命令：

```bash
cd /path/to/kiro-router
uv tool install . --global
```

验证安装：

```bash
kiro-gateway --version
```

### 安装服务

```bash
cd macos-service
./install-macos-service.sh
```

安装脚本会：
1. 检查 `kiro-gateway` 是否已安装
2. 提示输入 `.env` 配置文件路径（默认使用当前目录的 `.env`）
3. 创建必要的目录和配置文件
4. 加载并启动服务

### 验证服务

```bash
./kiro-gateway-service.sh status
```

访问健康检查端点：

```bash
curl http://localhost:8000/health
```

## 服务管理

### 启动服务

```bash
./kiro-gateway-service.sh start
```

### 停止服务

```bash
./kiro-gateway-service.sh stop
```

### 重启服务

```bash
./kiro-gateway-service.sh restart
```

### 查看状态

```bash
./kiro-gateway-service.sh status
```

输出示例：

```
ℹ Service Status
  State: Running
  PID:   12345
  Memory: 45.2 MB
  Health: ✓ OK (http://localhost:8000/health)
```

### 查看日志

```bash
# 查看所有日志（stdout + stderr）
./kiro-gateway-service.sh logs

# 只查看 stdout
./kiro-gateway-service.sh logs stdout

# 只查看 stderr
./kiro-gateway-service.sh logs stderr
```

### 卸载服务

```bash
./kiro-gateway-service.sh uninstall
```

## 日志文件

日志文件位置：`~/Library/Logs/com.github.kirowhat.gateway/`

- **stdout.log**: 标准输出日志
- **stderr.log**: 错误输出日志

手动查看日志：

```bash
# 查看最近的日志
tail -f ~/Library/Logs/com.github.kirowhat.gateway/stdout.log

# 查看错误日志
tail -f ~/Library/Logs/com.github.kirowhat.gateway/stderr.log

# 查看最近的 100 行
tail -n 100 ~/Library/Logs/com.github.kirowhat.gateway/stderr.log
```

## 配置说明

### 环境变量

服务使用 `KIRO_ENV_FILE` 环境变量指定配置文件路径。安装时会自动配置。

### 服务配置

LaunchAgent 配置文件：`~/Library/LaunchAgents/com.github.kirowhat.gateway.plist`

主要配置项：

- **RunAtLoad**: 开机自动启动
- **KeepAlive**: 进程崩溃时自动重启
- **StandardOutPath**: 标准输出日志路径
- **StandardErrorPath**: 错误输出日志路径

### 修改配置

如果需要更改 `.env` 文件路径：

1. 卸载服务：`./kiro-gateway-service.sh uninstall`
2. 重新安装：`./install-macos-service.sh`
3. 输入新的 `.env` 文件路径

## 故障排查

### 服务无法启动

1. **检查日志**

```bash
./kiro-gateway-service.sh logs stderr
```

2. **验证配置文件**

确保 `.env` 文件存在且配置正确：

```bash
cat ~/.kiro-gateway/.env  # 或你指定的路径
```

3. **手动测试**

手动运行 `kiro-gateway` 查看错误：

```bash
kiro-gateway
```

### 服务启动但无法访问

1. **检查端口是否被占用**

```bash
lsof -i :8000
```

2. **检查防火墙设置**

确保端口 8000 未被防火墙阻止。

3. **验证健康检查**

```bash
curl http://localhost:8000/health
```

### 找不到 kiro-gateway 命令

重新安装 Kiro Gateway：

```bash
cd /path/to/kiro-router
uv tool install . --global --reinstall
```

### 权限问题

确保脚本有执行权限：

```bash
chmod +x macos-service/install-macos-service.sh
chmod +x macos-service/kiro-gateway-service.sh
```

## 与 Windows 版本对比

| 功能 | Windows | macOS |
|------|---------|-------|
| 启动脚本 | start-kiro-gateway.vbs | kiro-gateway-service.sh start |
| 环境变量 | VBScript 设置 | plist EnvironmentVariables |
| 后台运行 | WindowStyle Hidden | launchd daemon |
| 开机自启 | 注册表 Run key | RunAtLoad plist key |
| 日志输出 | 文件重定向 | StandardOutPath/ErrorPath |
| 进程监控 | VBScript 检查 | KeepAlive plist key |
| 安装方式 | 手动复制 VBS/脚本 | install-macos-service.sh |

## 技术细节

### LaunchAgent vs LaunchDaemon

- **LaunchAgent**: 用户级服务，只在用户登录时运行（本方案使用）
- **LaunchDaemon**: 系统级服务，需要 root 权限

### 进程隔离

服务在独立的 launchd 进程中运行，与终端完全分离。关闭终端不会影响服务运行。

### 自动重启

服务配置了 `KeepAlive`，当进程异常退出时会自动重启。重启间隔为 5 秒，避免频繁重启。

### 日志轮转

macOS 系统会自动处理日志轮转，但建议定期清理旧日志：

```bash
# 清理超过 7 天的日志
find ~/Library/Logs/com.github.kirowhat.gateway -name "*.log" -mtime +7 -delete
```

## 高级用法

### 自定义启动参数

如果需要自定义端口或主机地址：

1. 编辑 `.env` 文件：

```bash
SERVER_HOST=127.0.0.1
SERVER_PORT=9000
```

2. 重启服务：

```bash
./kiro-gateway-service.sh restart
```

### 多实例运行

如果需要运行多个实例（不同端口），需要修改服务名称：

1. 复制并修改 plist 模板
2. 修改 `Label` 为不同的名称（如 `com.github.kirowhat.gateway.2`）
3. 在 `.env` 中指定不同的端口

### 集成到其他工具

#### Claude Code

在 Claude Code 中配置：

```json
{
  "apiBase": "http://localhost:8000/v1",
  "apiKey": "your-proxy-api-key"
}
```

#### Cursor

在 Cursor 设置中配置 OpenAI API 端点：

```
Base URL: http://localhost:8000/v1
API Key: your-proxy-api-key
```

#### Cline

在 Cline 配置中使用：

```
OpenAI Base URL: http://localhost:8000/v1
API Key: your-proxy-api-key
```

## 卸载

完全卸载服务：

```bash
cd macos-service
./kiro-gateway-service.sh uninstall
```

手动清理残留文件：

```bash
# 删除配置
rm ~/Library/LaunchAgents/com.github.kirowhat.gateway.plist

# 删除日志
rm -rf ~/Library/Logs/com.github.kirowhat.gateway

# 卸载 kiro-gateway 命令
uv tool uninstall kiro-gateway
```

## 支持

遇到问题？

1. 查看 [故障排查](#故障排查) 章节
2. 检查日志文件
3. 访问 [GitHub Issues](https://github.com/jwadow/kiro-gateway/issues)

## 许可证

AGPL-3.0-or-later

与主项目保持一致。
