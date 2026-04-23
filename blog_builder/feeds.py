"""SEO and feed generation helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import html

from .utils import atom_text


def generate_sitemap(dist_dir, config, posts, categories, tags, slugify):
    """Generate sitemap.xml."""
    base_url = config.get("url", "").rstrip("/")
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    urls = [{"loc": f"{base_url}/", "lastmod": now, "priority": "1.0"}]
    for post in posts:
        lastmod = now
        if post.get("updated_at"):
            lastmod = post["updated_at"].strftime("%Y-%m-%dT%H:%M:%S+00:00")
        elif post.get("created_at"):
            lastmod = post["created_at"].strftime("%Y-%m-%dT%H:%M:%S+00:00")
        urls.append({"loc": f"{base_url}/posts/{post['slug']}/", "lastmod": lastmod, "priority": "0.8"})

    for category in categories:
        slug = slugify(category)
        urls.append({"loc": f"{base_url}/category/{slug}/", "lastmod": now, "priority": "0.5"})
    for tag in tags:
        slug = slugify(tag)
        urls.append({"loc": f"{base_url}/tag/{slug}/", "lastmod": now, "priority": "0.4"})

    urls.append({"loc": f"{base_url}/categories/", "lastmod": now, "priority": "0.5"})
    urls.append({"loc": f"{base_url}/tags/", "lastmod": now, "priority": "0.4"})
    urls.append({"loc": f"{base_url}/archives/", "lastmod": now, "priority": "0.5"})
    urls.append({"loc": f"{base_url}/about/", "lastmod": now, "priority": "0.3"})

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        lines.append("  <url>")
        lines.append(f'    <loc>{html.escape(url["loc"])}</loc>')
        lines.append(f'    <lastmod>{url["lastmod"]}</lastmod>')
        lines.append(f'    <priority>{url["priority"]}</priority>')
        lines.append("  </url>")
    lines.append("</urlset>")

    (Path(dist_dir) / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")
    print("sitemap.xml 已生成")


def generate_robots_txt(dist_dir, config):
    """Generate robots.txt."""
    base_url = config.get("url", "").rstrip("/")
    content = f"User-agent: *\nAllow: /\n\nSitemap: {base_url}/sitemap.xml\n"
    (Path(dist_dir) / "robots.txt").write_text(content, encoding="utf-8")
    print("robots.txt 已生成")


def generate_rss_feed(dist_dir, config, posts):
    """Generate Atom feed output."""
    base_url = config.get("url", "").rstrip("/")
    title = config.get("title", "Blog")
    description = config.get("description", "")
    author = config.get("author", "")
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom">']
    lines.append(f"  <title>{atom_text(title)}</title>")
    lines.append(f"  <subtitle>{atom_text(description)}</subtitle>")
    lines.append(f'  <link href="{atom_text(base_url)}/feed.xml" rel="self" type="application/atom+xml"/>')
    lines.append(f'  <link href="{atom_text(base_url)}/" rel="alternate" type="text/html"/>')
    lines.append(f"  <id>{atom_text(base_url)}/</id>")
    lines.append(f"  <updated>{now}</updated>")
    if author:
        lines.append(f"  <author><name>{atom_text(author)}</name></author>")

    for post in posts[:20]:
        post_url = f"{base_url}/posts/{post['slug']}/"
        updated = now
        if post.get("updated_at"):
            updated = post["updated_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
        elif post.get("created_at"):
            updated = post["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ")

        lines.append("  <entry>")
        lines.append(f'    <title>{atom_text(post["title"])}</title>')
        lines.append(f'    <link href="{atom_text(post_url)}" rel="alternate" type="text/html"/>')
        lines.append(f"    <id>{atom_text(post_url)}</id>")
        lines.append(f"    <updated>{updated}</updated>")
        if post.get("description"):
            lines.append(f'    <summary>{atom_text(post["description"])}</summary>')
        lines.append(f'    <content type="html">{atom_text(post["content"])}</content>')
        for tag in post.get("tags", []):
            lines.append(f'    <category term="{atom_text(tag)}"/>')
        lines.append("  </entry>")

    lines.append("</feed>")
    (Path(dist_dir) / "feed.xml").write_text("\n".join(lines), encoding="utf-8")
    print("Atom feed 已生成")
