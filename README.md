# 👻 Kiro Gateway

Kiro API（Amazon Q Developer）的代理网关，提供 OpenAI 和 Anthropic 兼容的 API 接口。

可配合 Claude Code、Cursor、Cline、Roo Code、OpenAI SDK、LangChain 等工具使用。

---

## 前置条件

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) 包管理器
- [kiro-cli](https://kiro.dev/cli/) 已安装并登录（`kiro-cli login`）

## 快速开始

```bash
git clone https://github.com/Gloriacnb/kiro-router.git
cd kiro-router
cp .env.example .env
```

编辑 `.env`，至少配置以下两项：

```env
# 你自定义的代理密码（连接时用作 api_key）
PROXY_API_KEY="your-secret-key"

# kiro-cli 数据库路径（推荐方式）
KIRO_CLI_DB_FILE="~/.local/share/kiro-cli/data.sqlite3"
```

然后启动：

```bash
uv sync
uv run python main.py
```

服务默认运行在 `http://localhost:8000`。

## 认证方式

`.env` 支持 4 种认证方式（任选其一）：

| 方式 | 配置项 | 说明 |
|------|--------|------|
| **kiro-cli 数据库**（推荐） | `KIRO_CLI_DB_FILE` | 指向 `~/.local/share/kiro-cli/data.sqlite3` |
| JSON 凭证文件 | `KIRO_CREDS_FILE` | 指向 `~/.aws/sso/cache/kiro-auth-token.json` |
| AWS SSO 缓存 | `KIRO_CREDS_FILE` | 指向 `~/.aws/sso/cache/` 下的 SSO 缓存文件 |
| Refresh Token | `REFRESH_TOKEN` | 直接填入 refresh token |

## 常用命令

```bash
# 自定义端口
uv run python main.py --port 9000

# 自定义 host（仅本地访问）
uv run python main.py --host 127.0.0.1

# 直接用 uvicorn
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

## 可用模型

> 模型可用性取决于你的 Kiro 订阅等级（免费/付费）。

| 模型 | 说明 |
|------|------|
| Claude Sonnet 4.5 | 均衡性能，适合编码和通用任务 |
| Claude Haiku 4.5 | 极速响应，适合简单任务和对话 |
| Claude Sonnet 4 | 上一代，依然可靠 |
| Claude 3.7 Sonnet | 旧版，向后兼容 |
| DeepSeek-V3.2 | 开源 MoE 模型，编码和推理均衡 |
| MiniMax M2.1 | 开源 MoE 模型，擅长复杂任务和规划 |
| Qwen3-Coder-Next | 开源 MoE 模型，专注编码 |

> 模型名称会自动标准化：`claude-sonnet-4-5`、`claude-sonnet-4.5`、`claude-sonnet-4-5-20250929` 都能识别。

## 客户端连接示例

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-secret-key"  # 你在 .env 中设置的 PROXY_API_KEY
)

response = client.chat.completions.create(
    model="claude-sonnet-4-5",
    messages=[{"role": "user", "content": "你好"}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### cURL

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'
```

### Claude Code

```bash
claude config set --global apiUrl http://localhost:8000/v1
claude config set --global model claude-sonnet-4-5
# 启动时会提示输入 API Key，填入你的 PROXY_API_KEY
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/v1/models` | GET | 模型列表 |
| `/v1/chat/completions` | POST | OpenAI 兼容接口 |
| `/v1/messages` | POST | Anthropic 兼容接口 |

## 调试

在 `.env` 中启用调试日志：

```env
DEBUG_MODE=errors   # 仅记录失败请求（推荐）
# DEBUG_MODE=all    # 记录所有请求
```

日志保存在 `debug_logs/` 目录。

## 许可证

AGPL-3.0 — 基于 [kiro-gateway](https://github.com/jwadow/kiro-gateway) 项目。
