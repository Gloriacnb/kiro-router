# -*- coding: utf-8 -*-

# Kiro Gateway
# https://github.com/jwadow/kiro-gateway
# Copyright (C) 2025 Jwadow
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Kiro Gateway - OpenAI-compatible interface for Kiro API.

Application entry point. Creates FastAPI app and connects routes.

Usage:
    # Using default settings (host: 0.0.0.0, port: 8000)
    python -m kiro

    # With CLI arguments (highest priority)
    python -m kiro --port 9000
    python -m kiro --host 127.0.0.1 --port 9000

    # Using uvicorn directly
    uvicorn kiro.__main__:app --host 0.0.0.0 --port 8000

Priority: CLI args > Environment variables > Default values
"""

import argparse
import logging
import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from kiro.config import (
    APP_TITLE,
    APP_DESCRIPTION,
    APP_VERSION,
    REFRESH_TOKEN,
    PROFILE_ARN,
    REGION,
    KIRO_CREDS_FILE,
    KIRO_CLI_DB_FILE,
    PROXY_API_KEY,
    DEFAULT_PROXY_API_KEY,
    LOG_LEVEL,
    SERVER_HOST,
    SERVER_PORT,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    STREAMING_READ_TIMEOUT,
    HIDDEN_MODELS,
    MODEL_ALIASES,
    HIDDEN_FROM_LIST,
    FALLBACK_MODELS,
    VPN_PROXY_URL,
    _warn_timeout_configuration,
)
from kiro.auth import KiroAuthManager
from kiro.cache import ModelInfoCache
from kiro.model_resolver import ModelResolver
from kiro.routes_openai import router as openai_router
from kiro.routes_anthropic import router as anthropic_router
from kiro.exceptions import validation_exception_handler
from kiro.debug_middleware import DebugLoggerMiddleware


# --- Loguru Configuration ---
logger.remove()
logger.add(
    sys.stderr,
    level=LOG_LEVEL,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


class InterceptHandler(logging.Handler):
    """
    Intercepts logs from standard logging and redirects them to loguru.

    Also filters out noisy shutdown-related exceptions (CancelledError, KeyboardInterrupt)
    that are normal during Ctrl+C but uvicorn logs as ERROR.
    """

    SHUTDOWN_EXCEPTIONS = (
        "CancelledError",
        "KeyboardInterrupt",
        "asyncio.exceptions.CancelledError",
    )

    def emit(self, record: logging.LogRecord) -> None:
        if record.exc_info:
            exc_type = record.exc_info[0]
            if exc_type is not None:
                exc_name = exc_type.__name__
                if exc_name in self.SHUTDOWN_EXCEPTIONS:
                    logger.info("Server shutdown in progress...")
                    return

        msg = record.getMessage()
        if any(exc in msg for exc in self.SHUTDOWN_EXCEPTIONS):
            return

        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging_intercept():
    loggers_to_intercept = [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
    ]

    for logger_name in loggers_to_intercept:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False


setup_logging_intercept()


# ==================================================================================================
# VPN/Proxy Configuration
# ==================================================================================================

if VPN_PROXY_URL:
    proxy_url_with_scheme = VPN_PROXY_URL if "://" in VPN_PROXY_URL else f"http://{VPN_PROXY_URL}"

    os.environ['HTTP_PROXY'] = proxy_url_with_scheme
    os.environ['HTTPS_PROXY'] = proxy_url_with_scheme
    os.environ['ALL_PROXY'] = proxy_url_with_scheme

    no_proxy_hosts = os.environ.get("NO_PROXY", "")
    local_hosts = "127.0.0.1,localhost"
    if no_proxy_hosts:
        os.environ["NO_PROXY"] = f"{no_proxy_hosts},{local_hosts}"
    else:
        os.environ["NO_PROXY"] = local_hosts

    logger.info(f"Proxy configured: {proxy_url_with_scheme}")
    logger.debug(f"NO_PROXY: {os.environ['NO_PROXY']}")


def validate_configuration() -> None:
    errors = []

    if PROXY_API_KEY == DEFAULT_PROXY_API_KEY:
        logger.warning("")
        logger.warning("⚠️  PROXY_API_KEY is using the default value!")
        logger.warning("   Anyone who knows this default can access your gateway.")
        logger.warning("   Set a unique PROXY_API_KEY in your .env file.")
        logger.warning("")

    env_file = Path(".env")

    has_refresh_token = bool(REFRESH_TOKEN)
    has_creds_file = bool(KIRO_CREDS_FILE)
    has_cli_db = bool(KIRO_CLI_DB_FILE)

    if KIRO_CREDS_FILE:
        creds_path = Path(KIRO_CREDS_FILE).expanduser()
        if not creds_path.exists():
            has_creds_file = False
            logger.warning(f"KIRO_CREDS_FILE not found: {KIRO_CREDS_FILE}")

    if KIRO_CLI_DB_FILE:
        cli_db_path = Path(KIRO_CLI_DB_FILE).expanduser()
        if not cli_db_path.exists():
            has_cli_db = False
            logger.warning(f"KIRO_CLI_DB_FILE not found: {KIRO_CLI_DB_FILE}")

    if not has_refresh_token and not has_creds_file and not has_cli_db:
        if not env_file.exists():
            errors.append(
                "No Kiro credentials configured!\n"
                "\n"
                "To get started:\n"
                "1. Create .env file:\n"
                "   cp .env.example .env\n"
                "\n"
                "2. Edit .env and configure your credentials:\n"
                "   2.1. Set you super-secret password as PROXY_API_KEY\n"
                "   2.2. Set your Kiro credentials:\n"
                "      - Option 1: KIRO_CREDS_FILE to your Kiro credentials JSON file\n"
                "      - Option 2: REFRESH_TOKEN from Kiro IDE traffic\n"
                "      - Option 3: KIRO_CLI_DB_FILE to kiro-cli SQLite database\n"
                "\n"
                "Or use environment variables (for Docker):\n"
                "   docker run -e PROXY_API_KEY=\"...\" -e REFRESH_TOKEN=\"...\" ...\n"
                "\n"
                "See README.md for detailed instructions."
            )
        else:
            errors.append(
                "No Kiro credentials configured!\n"
                "\n"
                "   Configure one of the following in your .env file:\n"
                "\n"
                "Set you super-secret password as PROXY_API_KEY\n"
                "   PROXY_API_KEY=\"my-super-secret-password-123\"\n"
                "\n"
                "   Option 1 (Recommended): JSON credentials file\n"
                "      KIRO_CREDS_FILE=\"path/to/your/kiro-credentials.json\"\n"
                "\n"
                "   Option 2: Refresh token\n"
                "      REFRESH_TOKEN=\"your_refresh_token_here\"\n"
                "\n"
                "   Option 3: kiro-cli SQLite database (AWS SSO)\n"
                "      KIRO_CLI_DB_FILE=\"~/.local/share/kiro-cli/data.sqlite3\"\n"
                "\n"
                "   See README.md for how to obtain credentials."
            )

    if errors:
        logger.error("")
        logger.error("=" * 60)
        logger.error("  CONFIGURATION ERROR")
        logger.error("=" * 60)
        for error in errors:
            for line in error.split('\n'):
                logger.error(f"  {line}")
        logger.error("=" * 60)
        logger.error("")
        sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application... Creating state managers.")

    limits = httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=30.0
    )
    timeout = httpx.Timeout(
        connect=30.0,
        read=STREAMING_READ_TIMEOUT,
        write=30.0,
        pool=30.0
    )
    app.state.http_client = httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        follow_redirects=True
    )
    logger.info("Shared HTTP client created with connection pooling")

    app.state.auth_manager = KiroAuthManager(
        refresh_token=REFRESH_TOKEN,
        profile_arn=PROFILE_ARN,
        region=REGION,
        creds_file=KIRO_CREDS_FILE if KIRO_CREDS_FILE else None,
        sqlite_db=KIRO_CLI_DB_FILE if KIRO_CLI_DB_FILE else None,
    )

    app.state.model_cache = ModelInfoCache()

    logger.info("Loading models from Kiro API...")
    try:
        token = await app.state.auth_manager.get_access_token()
        from kiro.utils import get_kiro_headers
        from kiro.auth import AuthType
        headers = get_kiro_headers(app.state.auth_manager, token)

        params = {"origin": "AI_EDITOR"}
        if app.state.auth_manager.auth_type == AuthType.KIRO_DESKTOP and app.state.auth_manager.profile_arn:
            params["profileArn"] = app.state.auth_manager.profile_arn

        list_models_url = f"{app.state.auth_manager.q_host}/ListAvailableModels"
        logger.debug(f"Fetching models from: {list_models_url}")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                list_models_url,
                headers=headers,
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                models_list = data.get("models", [])
                await app.state.model_cache.update(models_list)
                logger.debug(f"Successfully loaded {len(models_list)} models from Kiro API")
            else:
                raise Exception(f"HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to fetch models from Kiro API: {e}")
        logger.error("Using pre-configured fallback models. Not all models may be available on your plan, or the list may be outdated.")

        await app.state.model_cache.update(FALLBACK_MODELS)
        logger.debug(f"Loaded {len(FALLBACK_MODELS)} fallback models")

    for display_name, internal_id in HIDDEN_MODELS.items():
        app.state.model_cache.add_hidden_model(display_name, internal_id)

    if HIDDEN_MODELS:
        logger.debug(f"Added {len(HIDDEN_MODELS)} hidden models to cache")

    all_models = app.state.model_cache.get_all_model_ids()
    logger.info(f"Model cache ready: {len(all_models)} models total")

    app.state.model_resolver = ModelResolver(
        cache=app.state.model_cache,
        hidden_models=HIDDEN_MODELS,
        aliases=MODEL_ALIASES,
        hidden_from_list=HIDDEN_FROM_LIST
    )
    logger.info("Model resolver initialized")

    if MODEL_ALIASES:
        logger.debug(f"Model aliases configured: {list(MODEL_ALIASES.keys())}")
    if HIDDEN_FROM_LIST:
        logger.debug(f"Models hidden from list: {HIDDEN_FROM_LIST}")

    yield

    logger.info("Shutting down application...")
    try:
        await app.state.http_client.aclose()
        logger.info("Shared HTTP client closed")
    except Exception as e:
        logger.warning(f"Error closing shared HTTP client: {e}")


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(DebugLoggerMiddleware)

app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(openai_router)
app.include_router(anthropic_router)


UVICORN_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "default": {
            "class": "kiro.__main__.InterceptHandler",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
}


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{APP_TITLE} - {APP_DESCRIPTION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration Priority (highest to lowest):
  1. CLI arguments (--host, --port)
  2. Environment variables (SERVER_HOST, SERVER_PORT)
  3. Default values (0.0.0.0:8000)

Examples:
  kiro-gateway                            # Use defaults or env vars
  kiro-gateway --port 9000               # Override port only
  kiro-gateway --host 127.0.0.1          # Local connections only
  kiro-gateway -H 0.0.0.0 -p 8080        # Short form
        """
    )

    parser.add_argument(
        "-H", "--host",
        type=str,
        default=None,
        metavar="HOST",
        help=f"Server host address (default: {DEFAULT_SERVER_HOST}, env: SERVER_HOST)"
    )

    parser.add_argument(
        "-p", "--port",
        type=int,
        default=None,
        metavar="PORT",
        help=f"Server port (default: {DEFAULT_SERVER_PORT}, env: SERVER_PORT)"
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {APP_VERSION}"
    )

    return parser.parse_args()


def resolve_server_config(args: argparse.Namespace) -> tuple[str, int]:
    if args.host is not None:
        final_host = args.host
        host_source = "CLI argument"
    elif SERVER_HOST != DEFAULT_SERVER_HOST:
        final_host = SERVER_HOST
        host_source = "environment variable"
    else:
        final_host = DEFAULT_SERVER_HOST
        host_source = "default"

    if args.port is not None:
        final_port = args.port
        port_source = "CLI argument"
    elif SERVER_PORT != DEFAULT_SERVER_PORT:
        final_port = SERVER_PORT
        port_source = "environment variable"
    else:
        final_port = DEFAULT_SERVER_PORT
        port_source = "default"

    logger.debug(f"Host: {final_host} (from {host_source})")
    logger.debug(f"Port: {final_port} (from {port_source})")

    return final_host, final_port


def print_startup_banner(host: str, port: int) -> None:
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    display_host = "localhost" if host == "0.0.0.0" else host
    url = f"http://{display_host}:{port}"

    print()
    print(f"  {WHITE}{BOLD}👻 {APP_TITLE} v{APP_VERSION}{RESET}")
    print()
    print(f"  {WHITE}Server running at:{RESET}")
    print(f"  {GREEN}{BOLD}➜  {url}{RESET}")
    print()
    print(f"  {DIM}API Docs:      {url}/docs{RESET}")
    print(f"  {DIM}Health Check:  {url}/health{RESET}")
    print()
    print(f"  {DIM}{'─' * 48}{RESET}")
    print(f"  {WHITE}💬 Found a bug? Need help? Have questions?{RESET}")
    print(f"  {YELLOW}➜  https://github.com/jwadow/kiro-gateway/issues{RESET}")
    print(f"  {DIM}{'─' * 48}{RESET}")
    print()


def main() -> None:
    validate_configuration()
    _warn_timeout_configuration()
    args = parse_cli_args()
    final_host, final_port = resolve_server_config(args)
    print_startup_banner(final_host, final_port)
    logger.info(f"Starting Uvicorn server on {final_host}:{final_port}...")
    uvicorn.run(
        "kiro.__main__:app",
        host=final_host,
        port=final_port,
        log_config=UVICORN_LOG_CONFIG,
    )


if __name__ == "__main__":
    main()
