"""Markdown parsing and post metadata extraction."""

from __future__ import annotations

import html
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse

import markdown
import yaml

from .search import extract_search_paragraphs
from .utils import parse_timestamp_value, resolve_frontmatter_value


class ContentProcessor:
    """Parse markdown files into normalized post dictionaries."""

    VIDEO_FILE_EXTENSIONS = (".mp4", ".webm", ".ogg", ".ogv", ".mov", ".m4v")
    CREATED_AT_KEYS = ("create_time", "date created", "created_at", "date")
    UPDATED_AT_KEYS = ("update_time", "date modified", "updated_at", "modified")

    def __init__(self):
        self.md = markdown.Markdown(
            extensions=[
                "fenced_code",
                "tables",
                "toc",
                "meta",
            ]
        )

    def validate_post(self, post, filepath):
        """Validate metadata so malformed input fails fast."""
        if len(post.get("title", "")) > 200:
            raise ValueError(f"标题过长 (>200字符): {filepath}")

        tags = post.get("tags", [])
        if len(tags) > 20:
            raise ValueError(f"标签过多 (>20个): {filepath}")

        for tag in tags:
            if len(str(tag)) > 50:
                raise ValueError(f"标签过长: {filepath}")

        if len(post.get("description", "")) > 500:
            raise ValueError(f"描述过长 (>500字符): {filepath}")

        return True

    def resolve_post_created_at(self, frontmatter):
        for key in self.CREATED_AT_KEYS:
            parsed = parse_timestamp_value(frontmatter.get(key))
            if parsed is not None:
                return parsed
        return None

    def resolve_post_updated_at(self, frontmatter):
        for key in self.UPDATED_AT_KEYS:
            parsed = parse_timestamp_value(frontmatter.get(key))
            if parsed is not None:
                return parsed
        return None

    def normalize_media_src(self, src):
        parsed = urlparse(src)
        path_parts = parsed.path.lstrip("/").split("/")

        if parsed.scheme != "https" or parsed.netloc != "github.com":
            return src
        if len(path_parts) < 5 or path_parts[2] != "raw":
            return src

        owner, repo, _, branch, *asset_path = path_parts
        normalized_path = "/".join([owner, repo, branch, *asset_path])
        return urlunparse(("https", "raw.githubusercontent.com", f"/{normalized_path}", "", parsed.query, ""))

    def is_video_file_url(self, src):
        parsed = urlparse(src)
        return parsed.path.lower().endswith(self.VIDEO_FILE_EXTENSIONS)

    def get_video_mime_type(self, src):
        ext = Path(urlparse(src).path).suffix.lower()
        return {
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".ogg": "video/ogg",
            ".ogv": "video/ogg",
            ".mov": "video/quicktime",
            ".m4v": "video/mp4",
        }.get(ext, "video/mp4")

    def ensure_tag_attribute(self, tag, name, value):
        if re.search(rf"\b{name}\s*=", tag, flags=re.IGNORECASE):
            return tag
        return re.sub(r"\s*/?>$", f' {name}="{value}"\\g<0>', tag)

    def ensure_boolean_attribute(self, tag, name):
        if re.search(rf"\b{name}\b", tag, flags=re.IGNORECASE):
            return tag
        return re.sub(r"\s*/?>$", f" {name}\\g<0>", tag)

    def optimize_image_tag(self, match):
        tag = match.group(0)
        src_match = re.search(r'\bsrc=(["\'])(.*?)\1', tag, flags=re.IGNORECASE)

        if src_match:
            src = html.unescape(src_match.group(2))
            normalized_src = self.normalize_media_src(src)
            if normalized_src != src:
                escaped_src = html.escape(normalized_src, quote=True)
                tag = f"{tag[:src_match.start(2)]}{escaped_src}{tag[src_match.end(2):]}"

        tag = self.ensure_tag_attribute(tag, "loading", "lazy")
        tag = self.ensure_tag_attribute(tag, "decoding", "async")
        return tag

    def optimize_source_tag(self, match):
        tag = match.group(0)
        src_match = re.search(r'\bsrc=(["\'])(.*?)\1', tag, flags=re.IGNORECASE)
        if not src_match:
            return tag

        src = html.unescape(src_match.group(2))
        normalized_src = self.normalize_media_src(src)
        if normalized_src == src:
            return tag

        escaped_src = html.escape(normalized_src, quote=True)
        return f"{tag[:src_match.start(2)]}{escaped_src}{tag[src_match.end(2):]}"

    def optimize_video_tag(self, match):
        tag = self.optimize_source_tag(match)
        tag = self.ensure_boolean_attribute(tag, "controls")
        tag = self.ensure_boolean_attribute(tag, "playsinline")
        tag = self.ensure_tag_attribute(tag, "preload", "metadata")
        return tag

    def optimize_iframe_tag(self, match):
        tag = match.group(0)
        tag = self.ensure_tag_attribute(tag, "loading", "lazy")
        tag = self.ensure_tag_attribute(tag, "referrerpolicy", "strict-origin-when-cross-origin")
        tag = self.ensure_tag_attribute(
            tag,
            "allow",
            "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share",
        )
        tag = self.ensure_boolean_attribute(tag, "allowfullscreen")
        return tag

    def get_video_embed_url(self, src):
        parsed = urlparse(src)
        host = parsed.netloc.lower().removeprefix("www.")
        path = parsed.path.rstrip("/")
        query = parse_qs(parsed.query)

        if host in {"youtube.com", "m.youtube.com"}:
            if path == "/watch":
                video_id = query.get("v", [""])[0]
            elif path.startswith("/shorts/"):
                video_id = path.split("/shorts/", 1)[1]
            elif path.startswith("/embed/"):
                video_id = path.split("/embed/", 1)[1]
            else:
                video_id = ""

            if video_id:
                return f"https://www.youtube.com/embed/{video_id}"

        if host == "youtu.be":
            video_id = path.lstrip("/")
            if video_id:
                return f"https://www.youtube.com/embed/{video_id}"

        if host == "bilibili.com" or host.endswith(".bilibili.com"):
            match = re.search(r"/video/([^/?]+)", path)
            if match:
                bvid = match.group(1)
                page = query.get("p", ["1"])[0]
                return f"https://player.bilibili.com/player.html?bvid={bvid}&page={page}"

        return ""

    @staticmethod
    def strip_html_tags(text):
        return re.sub(r"<[^>]+>", "", html.unescape(text or "")).strip()

    def replace_link_only_paragraph_with_embed(self, match):
        href = html.unescape(match.group("href")).strip()
        text = self.strip_html_tags(match.group("text"))
        caption = text if text and text != href else ""

        if self.is_video_file_url(href):
            normalized_src = html.escape(self.normalize_media_src(href), quote=True)
            mime_type = html.escape(self.get_video_mime_type(href), quote=True)
            caption_html = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""
            return (
                '<figure class="post-embed post-embed-video">'
                '<video controls playsinline preload="metadata">'
                f'<source src="{normalized_src}" type="{mime_type}">'
                "当前浏览器不支持 video 标签播放该视频。"
                "</video>"
                f"{caption_html}"
                "</figure>"
            )

        embed_url = self.get_video_embed_url(href)
        if embed_url:
            title = caption or "Video embed"
            return (
                '<div class="post-embed post-embed-iframe">'
                f'<iframe src="{html.escape(embed_url, quote=True)}" '
                f'title="{html.escape(title, quote=True)}" '
                'loading="lazy" '
                'referrerpolicy="strict-origin-when-cross-origin" '
                'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
                "allowfullscreen></iframe>"
                "</div>"
            )

        return match.group(0)

    def optimize_content_html(self, html_content):
        html_content = re.sub(
            r'<p>\s*<a\b[^>]*\bhref=(["\'])(?P<href>.*?)\1[^>]*>(?P<text>.*?)</a>\s*</p>',
            self.replace_link_only_paragraph_with_embed,
            html_content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        html_content = re.sub(r"<img\b[^>]*>", self.optimize_image_tag, html_content, flags=re.IGNORECASE)
        html_content = re.sub(r"<source\b[^>]*>", self.optimize_source_tag, html_content, flags=re.IGNORECASE)
        html_content = re.sub(r"<video\b[^>]*>", self.optimize_video_tag, html_content, flags=re.IGNORECASE)
        html_content = re.sub(r"<iframe\b[^>]*>", self.optimize_iframe_tag, html_content, flags=re.IGNORECASE)
        return html_content

    def parse_markdown(self, filepath):
        """Parse a markdown file into a normalized post dictionary."""
        max_size = 10 * 1024 * 1024
        if os.path.getsize(filepath) > max_size:
            raise ValueError(f"文件过大 (>10MB): {filepath}")

        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()

        frontmatter = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                except yaml.YAMLError as error:
                    print(f"警告: YAML frontmatter 解析失败 ({filepath}): {error}")

        html_content = self.md.convert(body)
        toc_html = getattr(self.md, "toc", "")
        self.md.reset()
        html_content = self.optimize_content_html(html_content)

        plain_text = re.sub(r"<[^>]+>", "", html_content)
        plain_text = html.unescape(plain_text)
        char_count = len(re.sub(r"\s+", "", plain_text))
        reading_minutes = max(1, round(char_count / 400))

        filename = os.path.basename(filepath)
        default_title = os.path.splitext(filename)[0]
        title = str(resolve_frontmatter_value(frontmatter, "title", default_title)).strip() or default_title

        aliases = resolve_frontmatter_value(frontmatter, "aliases", title)
        if isinstance(aliases, str):
            aliases = [aliases.strip()] if aliases.strip() else [title]
        elif isinstance(aliases, list):
            aliases = [str(alias).strip() for alias in aliases if str(alias).strip()] or [title]
        else:
            alias_text = str(aliases).strip()
            aliases = [alias_text] if alias_text else [title]

        slug = str(resolve_frontmatter_value(frontmatter, "slug", title)).strip() or title
        category = frontmatter.get("category", "未分类")
        tags = frontmatter.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",")]
        description = frontmatter.get("description", "")
        draft = frontmatter.get("draft", False)
        created_at = self.resolve_post_created_at(frontmatter)
        updated_at = self.resolve_post_updated_at(frontmatter)

        explicit_date = parse_timestamp_value(frontmatter.get("date"))
        display_dt = explicit_date if explicit_date is not None else created_at
        post_date = display_dt.strftime("%Y-%m-%d") if display_dt is not None else None

        post = {
            "title": title,
            "aliases": aliases,
            "slug": slug,
            "date": post_date,
            "date_display": post_date,
            "created_at": created_at,
            "updated_at": updated_at,
            "category": category,
            "tags": tags,
            "description": description,
            "content": html_content,
            "toc": toc_html,
            "reading_time": reading_minutes,
            "search_entries": extract_search_paragraphs(html_content),
            "search_paragraphs": [],
            "draft": draft,
            "filepath": filepath,
            "filename": filename,
        }
        post["search_paragraphs"] = [entry["text"] for entry in post["search_entries"] if entry.get("text")]

        self.validate_post(post, filepath)
        return post
