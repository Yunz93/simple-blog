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
    from blog_builder.rendering import generate_categories
    from blog_builder.utils import slugify
    from jinja2 import Environment, FileSystemLoader
else:
    BlogBuilder = None


@unittest.skipIf(BlogBuilder is None, "build dependencies are not installed")
class BuildSmokeTests(unittest.TestCase):
    def create_temp_blog_root(self):
        repo_root = Path(__file__).resolve().parents[1]
        temp_dir = tempfile.TemporaryDirectory()
        temp_root = Path(temp_dir.name)
        shutil.copytree(repo_root / "template", temp_root / "template")
        shutil.copytree(repo_root / "static", temp_root / "static")
        shutil.copytree(repo_root / "blog_builder", temp_root / "blog_builder")
        shutil.copy2(repo_root / "build.py", temp_root / "build.py")
        (temp_root / "config.yaml").write_text(
            textwrap.dedent(
                """\
                title: "Tmp Blog"
                description: "Smoke test"
                author: "Tester"
                url: "https://example.com"
                posts_per_page: 10
                posts_source: "posts"
                footer: "Footer"
                """
            ),
            encoding="utf-8",
        )
        (temp_root / "posts").mkdir()
        return temp_dir, temp_root

    def test_builder_generates_core_outputs(self):
        temp_dir, temp_root = self.create_temp_blog_root()
        self.addCleanup(temp_dir.cleanup)
        posts_dir = temp_root / "posts"
        (posts_dir / "sample.md").write_text(
            textwrap.dedent(
                """\
                ---
                title: Smoke Title
                date: 2024-03-20
                category: 测试
                tags: [冒烟]
                description: Smoke Description
                ---

                ## Intro

                Smoke body.
                """
            ),
            encoding="utf-8",
        )

        cwd = os.getcwd()
        try:
            os.chdir(temp_root)
            builder = BlogBuilder()
            builder.build()
        finally:
            os.chdir(cwd)

        dist_dir = temp_root / "dist"
        self.assertTrue((dist_dir / "index.html").exists())
        self.assertTrue((dist_dir / "search.json").exists())
        self.assertTrue((dist_dir / "feed.xml").exists())
        self.assertTrue((dist_dir / "sitemap.xml").exists())
        self.assertTrue((dist_dir / "posts" / "smoke-title" / "index.html").exists())

        search_payload = json.loads((dist_dir / "search.json").read_text(encoding="utf-8"))
        self.assertEqual(search_payload[0]["slug"], "smoke-title")

    def test_builder_merges_categories_with_same_slug(self):
        repo_root = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_root = Path(tmp_dir)
            shutil.copytree(repo_root / "template", temp_root / "template")
            shutil.copytree(repo_root / "static", temp_root / "static")
            shutil.copytree(repo_root / "blog_builder", temp_root / "blog_builder")
            shutil.copy2(repo_root / "build.py", temp_root / "build.py")

            (temp_root / "config.yaml").write_text(
                textwrap.dedent(
                    """\
                    title: "Tmp Blog"
                    description: "Smoke test"
                    author: "Tester"
                    url: "https://example.com"
                    posts_per_page: 10
                    posts_source: "posts"
                    footer: "Footer"
                    """
                ),
                encoding="utf-8",
            )

            posts_dir = temp_root / "posts"
            posts_dir.mkdir()
            (posts_dir / "older.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    title: Older Post
                    date: 2024-03-20
                    category: Creation
                    tags: [冒烟]
                    description: Smoke Description
                    ---

                    Older body.
                    """
                ),
                encoding="utf-8",
            )
            (posts_dir / "newer.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    title: Newer Post
                    date: 2024-03-21
                    category: creation
                    tags: [冒烟]
                    description: Smoke Description
                    ---

                    Newer body.
                    """
                ),
                encoding="utf-8",
            )

            cwd = os.getcwd()
            try:
                os.chdir(temp_root)
                builder = BlogBuilder()
                builder.build()
            finally:
                os.chdir(cwd)

            categories_page = (temp_root / "dist" / "categories" / "index.html").read_text(encoding="utf-8")
            self.assertIn("Creation", categories_page)
            self.assertNotIn(">creation<", categories_page)
            self.assertEqual(categories_page.count('/category/creation/'), 1)

    def test_generate_categories_removes_stale_category_directories(self):
        repo_root = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_root = Path(tmp_dir)
            dist_dir = temp_root / "dist"
            dist_dir.mkdir()

            env = Environment(loader=FileSystemLoader(str(repo_root / "template")))
            env.filters["slugify"] = slugify
            env.globals["build_version"] = "test-build"
            config = {
                "title": "Tmp Blog",
                "description": "Smoke test",
                "author": "Tester",
                "url": "https://example.com",
                "footer": "Footer",
            }

            generate_categories(
                env,
                dist_dir,
                config,
                {"Old Category": [{"title": "Old", "category": "Old Category", "tags": []}]},
                {},
                slugify,
            )
            self.assertTrue((dist_dir / "category" / "old-category" / "index.html").exists())

            generate_categories(
                env,
                dist_dir,
                config,
                {"New Category": [{"title": "New", "category": "New Category", "tags": []}]},
                {},
                slugify,
            )

            self.assertFalse((dist_dir / "category" / "old-category").exists())
            self.assertTrue((dist_dir / "category" / "new-category" / "index.html").exists())

    def test_builder_rejects_ambiguous_category_slug_collisions(self):
        temp_dir, temp_root = self.create_temp_blog_root()
        self.addCleanup(temp_dir.cleanup)
        posts_dir = temp_root / "posts"
        (posts_dir / "c.md").write_text(
            textwrap.dedent(
                """\
                ---
                title: Category C
                date: 2024-03-20
                category: C
                tags: [冒烟]
                description: Smoke Description
                ---

                Body.
                """
            ),
            encoding="utf-8",
        )
        (posts_dir / "cpp.md").write_text(
            textwrap.dedent(
                """\
                ---
                title: Category C++
                date: 2024-03-21
                category: C++
                tags: [冒烟]
                description: Smoke Description
                ---

                Body.
                """
            ),
            encoding="utf-8",
        )

        cwd = os.getcwd()
        try:
            os.chdir(temp_root)
            builder = BlogBuilder()
            with self.assertRaisesRegex(ValueError, "分类 slug冲突"):
                builder.load_posts()
        finally:
            os.chdir(cwd)

    def test_builder_rejects_ambiguous_tag_slug_collisions(self):
        temp_dir, temp_root = self.create_temp_blog_root()
        self.addCleanup(temp_dir.cleanup)
        posts_dir = temp_root / "posts"
        (posts_dir / "c.md").write_text(
            textwrap.dedent(
                """\
                ---
                title: Tag C
                date: 2024-03-20
                category: 测试
                tags: [C]
                description: Smoke Description
                ---

                Body.
                """
            ),
            encoding="utf-8",
        )
        (posts_dir / "cpp.md").write_text(
            textwrap.dedent(
                """\
                ---
                title: Tag C++
                date: 2024-03-21
                category: 测试
                tags: [C++]
                description: Smoke Description
                ---

                Body.
                """
            ),
            encoding="utf-8",
        )

        cwd = os.getcwd()
        try:
            os.chdir(temp_root)
            builder = BlogBuilder()
            with self.assertRaisesRegex(ValueError, "标签 slug冲突"):
                builder.load_posts()
        finally:
            os.chdir(cwd)
