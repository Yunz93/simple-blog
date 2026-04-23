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

    def test_video_link_only_paragraph_becomes_embed(self):
        html = self.processor.optimize_content_html(
            '<p><a href="https://youtu.be/abc123">https://youtu.be/abc123</a></p>'
        )
        self.assertIn("youtube.com/embed/abc123", html)
