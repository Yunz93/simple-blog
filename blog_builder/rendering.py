"""Template rendering and page generation helpers."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path


def render_template(environment, dist_dir, template_name, context, output_path):
    """Render a Jinja template to the dist directory."""
    template = environment.get_template(template_name)
    rendered = template.render(**context)
    full_path = Path(dist_dir) / output_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(rendered, encoding="utf-8")


def remove_generated_path(dist_dir, output_path):
    """Remove a generated file or directory before re-rendering that section."""
    full_path = Path(dist_dir) / output_path
    if full_path.is_dir():
        shutil.rmtree(full_path)
    elif full_path.exists():
        full_path.unlink()


def build_index_page_url(page_number):
    if page_number <= 1:
        return "/"
    return f"/page/{page_number}/"


def build_pagination_context(current_page, total_pages):
    page_numbers = list(range(1, total_pages + 1))
    return {
        "current_page": current_page,
        "total_pages": total_pages,
        "page_numbers": page_numbers,
        "has_prev": current_page > 1,
        "has_next": current_page < total_pages,
        "prev_url": build_index_page_url(current_page - 1) if current_page > 1 else None,
        "next_url": build_index_page_url(current_page + 1) if current_page < total_pages else None,
        "page_url": build_index_page_url,
    }


def generate_index(environment, dist_dir, config, posts, categories, tags):
    posts_per_page = config.get("posts_per_page", 10)
    total_posts = len(posts)
    total_pages = max(1, math.ceil(total_posts / posts_per_page)) if posts_per_page > 0 else 1

    for page_number in range(1, total_pages + 1):
        start = (page_number - 1) * posts_per_page
        end = start + posts_per_page
        output_path = "index.html" if page_number == 1 else f"page/{page_number}/index.html"
        render_template(
            environment,
            dist_dir,
            "index.html",
            {
                "config": config,
                "posts": posts[start:end],
                "categories": categories,
                "tags": tags,
                "pagination": build_pagination_context(page_number, total_pages),
                "canonical_path": build_index_page_url(page_number),
            },
            output_path,
        )

    print(f"首页已生成，共 {total_pages} 页")


def generate_posts(environment, dist_dir, config, posts, categories, tags):
    for index, post in enumerate(posts):
        prev_post = posts[index - 1] if index > 0 else None
        next_post = posts[index + 1] if index < len(posts) - 1 else None
        output_path = f"posts/{post['slug']}/index.html"
        render_template(
            environment,
            dist_dir,
            "post.html",
            {
                "config": config,
                "post": post,
                "prev_post": prev_post,
                "next_post": next_post,
                "categories": categories,
                "tags": tags,
                "canonical_path": f"/posts/{post['slug']}/",
            },
            output_path,
        )
    print(f"生成了 {len(posts)} 篇文章页面")


def generate_categories(environment, dist_dir, config, categories, tags, slugify):
    remove_generated_path(dist_dir, "categories")
    remove_generated_path(dist_dir, "category")

    render_template(
        environment,
        dist_dir,
        "categories.html",
        {
            "config": config,
            "categories": categories,
            "tags": tags,
            "canonical_path": "/categories/",
        },
        "categories/index.html",
    )

    for category, posts in categories.items():
        slug = slugify(category)
        render_template(
            environment,
            dist_dir,
            "category.html",
            {
                "config": config,
                "category": category,
                "posts": posts,
                "categories": categories,
                "tags": tags,
                "canonical_path": f"/category/{slug}/",
            },
            f"category/{slug}/index.html",
        )
    print(f"生成了 {len(categories)} 个分类页面")


def generate_tags(environment, dist_dir, config, categories, tags, slugify):
    remove_generated_path(dist_dir, "tags")
    remove_generated_path(dist_dir, "tag")

    render_template(
        environment,
        dist_dir,
        "tags.html",
        {
            "config": config,
            "tags": tags,
            "categories": categories,
            "canonical_path": "/tags/",
        },
        "tags/index.html",
    )

    for tag, posts in tags.items():
        slug = slugify(tag)
        render_template(
            environment,
            dist_dir,
            "tag.html",
            {
                "config": config,
                "tag": tag,
                "posts": posts,
                "categories": categories,
                "tags": tags,
                "canonical_path": f"/tag/{slug}/",
            },
            f"tag/{slug}/index.html",
        )
    print(f"生成了 {len(tags)} 个标签页面")


def generate_search_data(dist_dir, posts):
    search_data = []
    for post in posts:
        date_str = post["date"]
        if hasattr(date_str, "strftime"):
            date_str = date_str.strftime("%Y-%m-%d")
        search_data.append(
            {
                "title": post["title"],
                "aliases": post.get("aliases", []),
                "slug": post["slug"],
                "description": post["description"],
                "search_paragraphs": post.get("search_paragraphs", []),
                "search_entries": post.get("search_entries", []),
                "category": post["category"],
                "tags": post["tags"],
                "date": date_str,
            }
        )

    output_path = Path(dist_dir) / "search.json"
    output_path.write_text(json.dumps(search_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("搜索数据已生成")


def post_archive_year(post):
    if post.get("created_at"):
        return post["created_at"].year
    for key in ("date_display", "date"):
        value = post.get(key)
        if not value:
            continue
        try:
            return int(str(value)[:4])
        except (ValueError, IndexError):
            continue
    return None


def generate_archive(environment, dist_dir, config, posts):
    archive = {}
    for post in posts:
        year = post_archive_year(post)
        archive.setdefault(year if year is not None else 0, []).append(post)

    sorted_years = sorted(archive.keys(), reverse=True)
    archive_sorted = [(year, archive[year]) for year in sorted_years]
    render_template(
        environment,
        dist_dir,
        "archive.html",
        {
            "config": config,
            "archive": archive_sorted,
            "total_posts": len(posts),
            "canonical_path": "/archives/",
        },
        "archives/index.html",
    )
    print("归档页面已生成")


def generate_about(environment, dist_dir, config, about_content):
    render_template(
        environment,
        dist_dir,
        "about.html",
        {
            "config": config,
            "about_content": about_content,
            "canonical_path": "/about/",
        },
        "about/index.html",
    )
    print("关于页面已生成")


def generate_404(environment, dist_dir, config):
    render_template(
        environment,
        dist_dir,
        "404.html",
        {
            "config": config,
            "canonical_path": "/404.html",
        },
        "404.html",
    )
    print("404 页面已生成")
