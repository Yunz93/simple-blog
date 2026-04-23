"""Static asset copy and cache-busting helpers."""

from __future__ import annotations

import re
import shutil
from pathlib import Path


def copy_static(static_dir, dist_dir, build_version):
    """Copy static assets into dist and rewrite immutable URLs with a version."""
    static_path = Path(static_dir)
    if not static_path.exists():
        return

    dist_static = Path(dist_dir) / "static"
    shutil.copytree(static_path, dist_static)
    version_static_assets(dist_static, build_version)
    print("静态资源已复制")


def version_static_assets(dist_static, build_version):
    """Add version query params to CSS-referenced assets."""
    css_path = dist_static / "css" / "style.css"
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
        css_content = css_content.replace(
            "../fonts/lxgwwenkai-regular/result.css",
            f"../fonts/lxgwwenkai-regular/result.css?v={build_version}",
        )
        css_content = css_content.replace(
            "../fonts/lxgwwenkai-medium/result.css",
            f"../fonts/lxgwwenkai-medium/result.css?v={build_version}",
        )
        css_content = css_content.replace("./jinkai.css", f"./jinkai.css?v={build_version}")
        css_path.write_text(css_content, encoding="utf-8")

    for font_css_path in dist_static.rglob("result.css"):
        font_css = font_css_path.read_text(encoding="utf-8")
        font_css = re.sub(
            r'url\((["\']?)(\./[^)"\']+\.woff2)\1\)',
            lambda match: f"url({match.group(1)}{match.group(2)}?v={build_version}{match.group(1)})",
            font_css,
        )
        font_css_path.write_text(font_css, encoding="utf-8")

    css_dir = dist_static / "css"
    if not css_dir.exists():
        return

    for legacy_font_css_path in css_dir.glob("*.css"):
        if legacy_font_css_path.name == "style.css":
            continue
        legacy_css = legacy_font_css_path.read_text(encoding="utf-8")
        legacy_css = re.sub(
            r'url\((["\']?)(\.\./[^)"\']+\.woff2)\1\)',
            lambda match: f"url({match.group(1)}{match.group(2)}?v={build_version}{match.group(1)})",
            legacy_css,
        )
        legacy_font_css_path.write_text(legacy_css, encoding="utf-8")
