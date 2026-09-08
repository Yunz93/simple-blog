import tempfile
import textwrap
import unittest
from importlib.util import find_spec
from pathlib import Path

if find_spec("markdown") is not None and find_spec("yaml") is not None:
    from blog_builder.content import ContentProcessor
else:
    ContentProcessor = None


@unittest.skipIf(ContentProcessor is None, "markdown/yaml dependencies are not installed")
class ContentProcessorTests(unittest.TestCase):
    def setUp(self):
        self.processor = ContentProcessor()

    def test_parse_markdown_extracts_metadata_and_search_entries(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            post_path = Path(tmp_dir) / "hello.md"
            post_path.write_text(
                textwrap.dedent(
                    """\
                    ---
                    title: Hello World
                    aliases:
                      - Greeting
                    date: 2024-03-18
                    category: 技术
                    tags: [Python, Web]
                    description: Example post
                    ---

                    ## Section One

                    First paragraph.
                    """
                ),
                encoding="utf-8",
            )

            post = self.processor.parse_markdown(str(post_path))

            self.assertEqual(post["title"], "Hello World")
            self.assertEqual(post["aliases"], ["Greeting"])
            self.assertEqual(post["date"], "2024-03-18")
            self.assertEqual(post["category"], "技术")
            self.assertEqual(post["tags"], ["Python", "Web"])
            self.assertTrue(post["search_entries"])
            self.assertEqual(post["search_entries"][0]["section_title"], "Section One")

    def test_parse_markdown_strips_leading_h1_that_repeats_title(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            post_path = Path(tmp_dir) / "dup-title.md"
            post_path.write_text(
                textwrap.dedent(
                    """\
                    ---
                    title: Duplicate Title
                    date: 2024-03-18
                    ---

                    # Duplicate Title

                    ## Section One

                    First paragraph.
                    """
                ),
                encoding="utf-8",
            )

            post = self.processor.parse_markdown(str(post_path))

            self.assertNotRegex(post["content"], r"<h1[^>]*>Duplicate Title</h1>")
            self.assertIn("Section One", post["content"])
            self.assertNotIn("Duplicate Title", post["toc"])
            self.assertEqual(post["search_entries"][0]["section_title"], "Section One")

    def test_parse_markdown_keeps_leading_h1_that_differs_from_title(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            post_path = Path(tmp_dir) / "kept-heading.md"
            post_path.write_text(
                textwrap.dedent(
                    """\
                    ---
                    title: Full Product Title
                    date: 2024-03-18
                    ---

                    # Short Brand

                    Body copy.
                    """
                ),
                encoding="utf-8",
            )

            post = self.processor.parse_markdown(str(post_path))

            self.assertRegex(post["content"], r"<h1[^>]*>Short Brand</h1>")

    def test_obsidian_image_alt_width_becomes_html_width(self):
        html = self.processor.optimize_content_html('<img alt="xx|300" src="xx.png">')
        self.assertIn('alt="xx"', html)
        self.assertIn('width="300"', html)
        self.assertIn("width: 300px", html)
        self.assertNotIn("|300", html)

    def test_obsidian_image_alt_width_and_height_become_attributes(self):
        html = self.processor.optimize_content_html('<img alt="cover|400x200" src="xx.png">')
        self.assertIn('alt="cover"', html)
        self.assertIn('width="400"', html)
        self.assertIn('height="200"', html)

    def test_plain_image_alt_is_not_treated_as_size(self):
        html = self.processor.optimize_content_html('<img alt="1.00" src="xx.png">')
        self.assertIn('alt="1.00"', html)
        self.assertNotIn("width=", html)

    def test_parse_markdown_applies_obsidian_image_width_syntax(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            post_path = Path(tmp_dir) / "sized.md"
            post_path.write_text(
                textwrap.dedent(
                    """\
                    ---
                    title: Sized Image
                    date: 2024-03-18
                    ---

                    ![xx|300](https://example.com/xx.png)
                    """
                ),
                encoding="utf-8",
            )

            post = self.processor.parse_markdown(str(post_path))

            self.assertIn('alt="xx"', post["content"])
            self.assertIn('width="300"', post["content"])
            self.assertNotIn("|300", post["content"])

    def test_parse_markdown_renders_list_immediately_after_paragraph(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            post_path = Path(tmp_dir) / "list.md"
            post_path.write_text(
                textwrap.dedent(
                    """\
                    ---
                    title: List Break
                    date: 2024-03-18
                    ---

                    其中：
                    - 微信公众号草稿：说明
                    - Simple Blog：说明
                    """
                ),
                encoding="utf-8",
            )

            post = self.processor.parse_markdown(str(post_path))

            self.assertIn("<ul>", post["content"])
            self.assertIn("<li>", post["content"])
            self.assertIn("微信公众号草稿", post["content"])
            self.assertNotRegex(post["content"], r"<p>[^<]*- 微信公众号草稿")

    def test_ensure_blank_line_before_lists_skips_fenced_code(self):
        body = "intro\n```\n- not a list\n```\n"
        result = self.processor.ensure_blank_line_before_lists(body)
        self.assertEqual(result, body)

    def test_video_link_only_paragraph_becomes_embed(self):
        html = self.processor.optimize_content_html(
            '<p><a href="https://youtu.be/abc123">https://youtu.be/abc123</a></p>'
        )
        self.assertIn("youtube.com/embed/abc123", html)
