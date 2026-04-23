# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Kiro Gateway 是一个 Python 代理网关，将 OpenAI 和 Anthropic 兼容的 API 请求转发到 Kiro（Amazon Q Developer）后端，使 Claude Code、Cursor、Cline 等工具可以通过 Kiro 使用 Claude 模型。

## 技术栈

- 运行时：Python 3.10+
- 框架：FastAPI + Uvicorn
- 包管理：`uv`
- HTTP 客户端：httpx
- 测试：pytest + pytest-asyncio

## 开发命令

```bash
# 安装依赖
uv sync

# 启动服务器
uv run python main.py
uv run python main.py --host 0.0.0.0 --port 9000

# 运行测试
pytest -v
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/unit/test_auth.py -v        # 单个测试文件
pytest -k "test_token_refresh" -v        # 按名称过滤
pytest --cov=kiro --cov-report=html      # 覆盖率报告
```

## 项目结构

```
kiro-router/
├── main.py              # 入口：FastAPI 应用、路由注册、日志、CLI 参数
├── kiro/                # 核心包
│   ├── auth.py          # KiroAuthManager：token 生命周期管理（到期前 10 分钟自动刷新）
│   ├── http_client.py   # KiroHttpClient：HTTP 请求 + 指数退避重试（429/5xx）
│   ├── cache.py         # ModelInfoCache：模型元数据缓存（1 小时 TTL）
│   ├── config.py        # 所有环境变量配置集中管理
│   ├── parsers.py       # AwsEventStreamParser：AWS SSE 二进制帧解析
│   ├── converters_core.py / streaming_core.py  # 共享的 Kiro 请求构建和流解析
│   ├── converters_openai.py / routes_openai.py / streaming_openai.py  # OpenAI 适配器
│   └── converters_anthropic.py / routes_anthropic.py / streaming_anthropic.py  # Anthropic 适配器
└── tests/
    ├── conftest.py      # block_all_network_calls fixture（所有测试网络隔离）
    ├── unit/            # 20+ 单元测试
    └── integration/     # 集成测试
```

## 架构：适配器模式

每个 API 格式由四个文件组成一组：`models_*.py` → `converters_*.py` → `routes_*.py` → `streaming_*.py`

请求流：
```
客户端请求 → routes_*.py → converters_*.py（借助 converters_core.py）
→ auth.py（获取 token）→ http_client.py（调用 Kiro API）
→ parsers.py → streaming_core.py → streaming_*.py → 客户端响应
```

新增 API 格式时，按此四文件模式实现，并在 `tests/unit/` 中添加对应测试。

## 配置

复制 `.env.example` 为 `.env`。认证方式优先级：

1. `KIRO_CLI_DB_FILE` — kiro-cli 的 SQLite 数据库路径（推荐）
2. `KIRO_CREDS_FILE` — JSON 凭证文件
3. `REFRESH_TOKEN` — 直接提供 refresh token

关键配置项：`PROXY_API_KEY`、`KIRO_REGION`（默认 `us-east-1`）、`DEBUG_MODE`（off/errors/all）、`FAKE_REASONING`、`TRUNCATION_RECOVERY`。

## 测试规范

所有测试通过 `conftest.py` 中的 `block_all_network_calls` fixture 实现完全网络隔离，不发起真实 API 请求。
