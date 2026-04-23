import unittest
from datetime import datetime

from blog_builder.utils import parse_timestamp_value, slugify, xml_10_safe_text


class UtilsTests(unittest.TestCase):
    def test_parse_timestamp_value_handles_obsidian_style_date(self):
        parsed = parse_timestamp_value("2024-03-17 Sun 15:44:48")
        self.assertEqual(parsed, datetime(2024, 3, 17, 15, 44, 48))

    def test_slugify_normalizes_punctuation_and_spaces(self):
        self.assertEqual(slugify("Hello, World! 你好"), "hello-world-你好")

    def test_xml_10_safe_text_removes_invalid_control_characters(self):
        self.assertEqual(xml_10_safe_text("ok\x08text"), "oktext")
