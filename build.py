#!/usr/bin/env python3
"""
Simple Blog - 静态博客构建工具
支持从 markdown-press 项目一键发布
"""

from __future__ import annotations

import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def main():
    try:
        from blog_builder import BlogBuilder
    except ModuleNotFoundError as error:
        missing_package = error.name or "未知依赖"
        print(
            "构建依赖缺失，请先执行 `bash ./build.sh` 或安装 `build-requirements.txt` 中的依赖。"
            f" 当前缺失: {missing_package}",
            file=sys.stderr,
        )
        raise SystemExit(1) from error

    builder = BlogBuilder()
    builder.build()


if __name__ == "__main__":
    main()
