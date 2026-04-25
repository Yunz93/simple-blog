"""Top-level site build orchestration."""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .assets import copy_static
from .constants import CONFIG_FILE, DIST_DIR, POSTS_DIR, STATIC_DIR, TEMPLATE_DIR
from .content import ContentProcessor
from .feeds import generate_robots_txt, generate_rss_feed, generate_sitemap
from .rendering import (
    generate_404,
    generate_about,
    generate_archive,
    generate_categories,
    generate_index,
    generate_posts,
    generate_search_data,
    generate_tags,
)
from .utils import slugify


class BlogBuilder:
    """Build the full static site into dist/."""

    def __init__(self):
        self.config = self.load_config()
        self.build_version = self.resolve_build_version()
        self.processor = ContentProcessor()
        self.about_md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "meta"])
        self.env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=select_autoescape(enabled_extensions=("html", "xml"), default_for_string=True),
        )
        self.env.globals["build_version"] = self.build_version
        self.env.filters["slugify"] = slugify
        self.posts = []
        self.categories = {}
        self.tags = {}

    @staticmethod
    def prefer_display_name(current_name, candidate_name):
        """Prefer a more intentional display name when terms only differ by case."""
        if current_name == candidate_name:
            return current_name

        if current_name.lower() == candidate_name.lower():
            if current_name.islower() and not candidate_name.islower():
                return candidate_name
            if candidate_name.istitle() and not current_name.istitle():
                return candidate_name

        return current_name

    @staticmethod
    def normalized_group_name(name):
        """Normalize group names for safe case-insensitive deduping."""
        return str(name).strip().casefold()

    @classmethod
    def resolve_group_name(cls, names_by_slug, group_name, group_type):
        """Return slug metadata for safe case-insensitive deduping."""
        slug = slugify(group_name) or group_name
        normalized_name = cls.normalized_group_name(group_name)
        existing = names_by_slug.get(slug)
        if existing is None:
            names_by_slug[slug] = (normalized_name, group_name)
            return slug, None, group_name

        existing_normalized, existing_display = existing
        if existing_normalized != normalized_name:
            raise ValueError(
                f"{group_type} slug冲突: {existing_display!r} 与 {group_name!r} 都映射到 {slug!r}"
            )

        preferred_name = cls.prefer_display_name(existing_display, group_name)
        if preferred_name != existing_display:
            names_by_slug[slug] = (existing_normalized, preferred_name)
        return slug, existing_display, preferred_name

    def group_categories(self):
        """Group posts by category slug so casing changes do not create duplicates."""
        grouped_categories = {}
        category_names_by_slug = {}

        for post in self.posts:
            category_name = str(post.get("category") or "未分类").strip() or "未分类"
            _, previous_name, canonical_name = self.resolve_group_name(
                category_names_by_slug, category_name, "分类"
            )
            if previous_name and previous_name != canonical_name and previous_name in grouped_categories:
                grouped_categories[canonical_name] = grouped_categories.pop(previous_name)
            grouped_categories.setdefault(canonical_name, []).append(post)

        return grouped_categories

    def group_tags(self):
        """Group tags by slug so equivalent spellings share one landing page."""
        grouped_tags = {}
        tag_names_by_slug = {}

        for post in self.posts:
            for raw_tag in post["tags"]:
                tag_name = str(raw_tag).strip()
                if not tag_name:
                    continue
                _, previous_name, canonical_name = self.resolve_group_name(
                    tag_names_by_slug, tag_name, "标签"
                )
                if previous_name and previous_name != canonical_name and previous_name in grouped_tags:
                    grouped_tags[canonical_name] = grouped_tags.pop(previous_name)
                grouped_tags.setdefault(canonical_name, []).append(post)

        return grouped_tags

    def resolve_build_version(self):
        vercel_sha = os.environ.get("VERCEL_GIT_COMMIT_SHA", "").strip()
        if vercel_sha:
            return vercel_sha[:12]

        git_sha = os.environ.get("GIT_COMMIT_SHA", "").strip()
        if git_sha:
            return git_sha[:12]

        return datetime.now(UTC).strftime("%Y%m%d%H%M%S")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                return yaml.safe_load(file)
        return {
            "title": "Simple Blog",
            "description": "简洁现代的静态博客",
            "author": "Author",
            "url": "https://example.com",
            "posts_per_page": 10,
        }

    def load_posts(self):
        posts_source = self.config.get("posts_source", POSTS_DIR)
        posts_path = Path(posts_source)

        if not posts_path.exists():
            posts_path = Path(POSTS_DIR)
            if not posts_path.exists():
                print(f"文章目录不存在: {posts_source} 或 {POSTS_DIR}")
                return
            print(f"使用默认文章目录: {POSTS_DIR}")
        else:
            print(f"使用文章源目录: {posts_source}")

        self.posts = []
        self.categories = {}
        self.tags = {}

        for md_file in sorted(posts_path.rglob("*.md")):
            post = self.processor.parse_markdown(str(md_file))
            post["slug"] = slugify(post["slug"]) or slugify(post["title"]) or "post"
            if not post["draft"]:
                self.posts.append(post)

        self.posts.sort(
            key=lambda post: (
                post["created_at"] is not None,
                post["created_at"] or datetime.min,
                post["date"] or "",
            ),
            reverse=True,
        )

        self.categories = self.group_categories()
        self.tags = self.group_tags()

        print(f"加载了 {len(self.posts)} 篇文章")
        print(f"分类: {list(self.categories.keys())}")
        print(f"标签: {list(self.tags.keys())}")

    def clean_dist(self):
        if os.path.exists(DIST_DIR):
            shutil.rmtree(DIST_DIR)
        os.makedirs(DIST_DIR)

    def render_about_content(self):
        about_content = ""
        about_md = Path("about.md")
        if about_md.exists():
            about_content = self.about_md.convert(about_md.read_text(encoding="utf-8"))
            self.about_md.reset()
        return about_content

    def build(self):
        print("=" * 50)
        print("Simple Blog 构建开始")
        print("=" * 50)

        self.clean_dist()
        self.load_posts()
        copy_static(STATIC_DIR, DIST_DIR, self.build_version)
        generate_index(self.env, DIST_DIR, self.config, self.posts, self.categories, self.tags)
        generate_posts(self.env, DIST_DIR, self.config, self.posts, self.categories, self.tags)
        generate_categories(self.env, DIST_DIR, self.config, self.categories, self.tags, slugify)
        generate_tags(self.env, DIST_DIR, self.config, self.categories, self.tags, slugify)
        generate_search_data(DIST_DIR, self.posts)
        generate_sitemap(DIST_DIR, self.config, self.posts, self.categories, self.tags, slugify)
        generate_robots_txt(DIST_DIR, self.config)
        generate_rss_feed(DIST_DIR, self.config, self.posts)
        generate_archive(self.env, DIST_DIR, self.config, self.posts)
        generate_about(self.env, DIST_DIR, self.config, self.render_about_content())
        generate_404(self.env, DIST_DIR, self.config)

        print("=" * 50)
        print(f"构建完成！输出目录: {DIST_DIR}")
        print("=" * 50)
