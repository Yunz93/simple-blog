import json
import os
import shutil
import tempfile
import textwrap
import unittest
from importlib.util import find_spec
from pathlib import Path

if all(find_spec(module) is not None for module in ("markdown", "yaml", "jinja2")):
    from blog_builder.builder import BlogBuilder
else:
    BlogBuilder = None


@unittest.skipIf(BlogBuilder is None, "build dependencies are not installed")
class RenderingSafetyTests(unittest.TestCase):
    def build_temp_site(self, config_text, post_text):
        repo_root = Path(__file__).resolve().parents[1]

        temp_dir = tempfile.TemporaryDirectory()
        temp_root = Path(temp_dir.name)
        shutil.copytree(repo_root / "template", temp_root / "template")
        shutil.copytree(repo_root / "static", temp_root / "static")
        shutil.copytree(repo_root / "blog_builder", temp_root / "blog_builder")
        shutil.copy2(repo_root / "build.py", temp_root / "build.py")

        (temp_root / "config.yaml").write_text(textwrap.dedent(config_text), encoding="utf-8")
        posts_dir = temp_root / "posts"
        posts_dir.mkdir()
        (posts_dir / "sample.md").write_text(textwrap.dedent(post_text), encoding="utf-8")

        cwd = os.getcwd()
        try:
            os.chdir(temp_root)
            builder = BlogBuilder()
            builder.build()
        finally:
            os.chdir(cwd)

        return temp_dir, temp_root

    def test_builder_autoescapes_metadata_but_keeps_post_html_content(self):
        temp_dir, temp_root = self.build_temp_site(
            """\
            title: "<script>alert('cfg')</script>"
            description: "<img src=x onerror=alert('cfg-desc')>"
            author: "Tester"
            url: "https://example.com"
            posts_per_page: 10
            posts_source: "posts"
            footer: "Footer"
            """,
            """\
            ---
            title: "<em>Unsafe Title</em>"
            date: 2024-03-20
            category: "测试"
            tags: [安全]
            description: "<img src=x onerror=alert('post-desc')>"
            ---

            <div class="custom-html">Inline HTML</div>
            """,
        )
        self.addCleanup(temp_dir.cleanup)

        index_html = (temp_root / "dist" / "index.html").read_text(encoding="utf-8")
        post_html = (temp_root / "dist" / "posts" / "emunsafe-titleem" / "index.html").read_text(encoding="utf-8")

        self.assertIn("&lt;script&gt;alert", index_html)
        self.assertNotIn("<script>alert('cfg')</script>", index_html)
        self.assertIn("&lt;em&gt;Unsafe Title&lt;/em&gt;", post_html)
        self.assertNotIn("<h1 class=\"post-title\"><em>Unsafe Title</em></h1>", post_html)
        self.assertIn("&lt;img src=x onerror=alert", post_html)
        self.assertIn('<div class="custom-html">Inline HTML</div>', post_html)

    def test_search_payload_uses_compact_entries_only(self):
        temp_dir, temp_root = self.build_temp_site(
            """\
            title: "Tmp Blog"
            description: "Search payload test"
            author: "Tester"
            url: "https://example.com"
            posts_per_page: 10
            posts_source: "posts"
            footer: "Footer"
            """,
            """\
            ---
            title: Search Test
            aliases: [Lookup]
            date: 2024-03-20
            category: 测试
            tags: [搜索]
            description: Search Description
            ---

            ## Section One

            First paragraph.
            """,
        )
        self.addCleanup(temp_dir.cleanup)

        search_json_path = temp_root / "dist" / "search.json"
        search_json_raw = search_json_path.read_text(encoding="utf-8")
        payload = json.loads(search_json_raw)

        self.assertEqual(payload[0]["aliases"], ["Lookup"])
        self.assertIn("search_entries", payload[0])
        self.assertNotIn("search_paragraphs", payload[0])
        self.assertNotIn("\n  ", search_json_raw)


class DeploymentConfigTests(unittest.TestCase):
    def test_vercel_json_sets_cache_headers_for_generated_feeds_and_search(self):
        repo_root = Path(__file__).resolve().parents[1]
        vercel_config = json.loads((repo_root / "vercel.json").read_text(encoding="utf-8"))
        headers_by_source = {entry["source"]: entry["headers"] for entry in vercel_config["headers"]}

        self.assertEqual(
            headers_by_source["/search.json"][0]["value"],
            "public, max-age=3600, stale-while-revalidate=86400",
        )
        self.assertEqual(
            headers_by_source["/feed.xml"][0]["value"],
            "public, max-age=3600, stale-while-revalidate=86400",
        )
        self.assertEqual(
            headers_by_source["/sitemap.xml"][0]["value"],
            "public, max-age=3600, stale-while-revalidate=86400",
        )
