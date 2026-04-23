# -*- coding: utf-8 -*-
# Compatibility shim — real entry point is kiro/__main__.py
# This file exists so `python main.py` and `uvicorn main:app` still work locally.

from kiro.__main__ import app, main, InterceptHandler  # noqa: F401

if __name__ == "__main__":
    main()
