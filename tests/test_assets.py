import tempfile
import unittest
from pathlib import Path

from blog_builder.assets import copy_static


class AssetCopyTests(unittest.TestCase):
    def test_copy_static_keeps_regular_font_bundle_and_versions_urls(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            static_dir = root / "static"
            dist_dir = root / "dist"

            (static_dir / "css").mkdir(parents=True)
            (static_dir / "fonts" / "lxgwwenkai-regular").mkdir(parents=True)
            (static_dir / "fonts" / "lxgwwenkai-medium").mkdir(parents=True)

            (static_dir / "css" / "style.css").write_text(
                "\n".join(
                    [
                        "@import url('../fonts/lxgwwenkai-regular/result.css');",
                        "@import url('../fonts/lxgwwenkai-medium/result.css');",
                    ]
                ),
                encoding="utf-8",
            )
            (static_dir / "fonts" / "lxgwwenkai-regular" / "result.css").write_text(
                '@font-face{src:url("./0.woff2") format("woff2")}',
                encoding="utf-8",
            )
            (static_dir / "fonts" / "lxgwwenkai-medium" / "result.css").write_text(
                '@font-face{src:url("./1.woff2") format("woff2")}',
                encoding="utf-8",
            )

            copy_static(static_dir, dist_dir, "build123")

            copied_regular_css = dist_dir / "static" / "fonts" / "lxgwwenkai-regular" / "result.css"
            self.assertTrue(copied_regular_css.exists())
            self.assertIn('?v=build123', copied_regular_css.read_text(encoding="utf-8"))

            copied_style_css = dist_dir / "static" / "css" / "style.css"
            self.assertIn(
                "../fonts/lxgwwenkai-regular/result.css?v=build123",
                copied_style_css.read_text(encoding="utf-8"),
            )

