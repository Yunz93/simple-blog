"""Search index extraction helpers."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser


class SearchContentParser(HTMLParser):
    """Extract searchable content blocks and their nearest section heading."""

    HEADING_TAGS = {f"h{index}" for index in range(1, 7)}
    TEXT_BLOCK_TAGS = {"p", "li", "pre", "td", "th"}
    IGNORED_TAGS = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.entries = []
        self.current_section_title = ""
        self.current_section_anchor = ""
        self.current_heading = None
        self.block_stack = []
        self.ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORED_TAGS:
            self.ignored_depth += 1
            return

        if self.ignored_depth:
            return

        attrs_dict = dict(attrs)
        if tag in self.HEADING_TAGS:
            self.current_heading = {"anchor": attrs_dict.get("id", ""), "chunks": []}
        elif tag in self.TEXT_BLOCK_TAGS:
            self.block_stack.append({"tag": tag, "chunks": []})

    def handle_endtag(self, tag):
        if tag in self.IGNORED_TAGS:
            self.ignored_depth = max(0, self.ignored_depth - 1)
            return

        if self.ignored_depth:
            return

        if tag in self.HEADING_TAGS and self.current_heading is not None:
            heading_text = self.clean_text("".join(self.current_heading["chunks"]))
            if heading_text:
                self.current_section_title = heading_text
                self.current_section_anchor = self.current_heading["anchor"]
            self.current_heading = None
            return

        if self.block_stack and self.block_stack[-1]["tag"] == tag:
            block = self.block_stack.pop()
            text = self.clean_text("".join(block["chunks"]))
            if text:
                self.entries.append(
                    {
                        "text": text,
                        "section_title": self.current_section_title,
                        "section_anchor": self.current_section_anchor,
                    }
                )

    def handle_data(self, data):
        if self.ignored_depth or not data:
            return

        if self.current_heading is not None:
            self.current_heading["chunks"].append(data)
        elif self.block_stack:
            self.block_stack[-1]["chunks"].append(data)

    @staticmethod
    def clean_text(text):
        return re.sub(r"\s+", " ", text).strip()


def extract_search_paragraphs(html_content):
    """Extract text entries with section metadata from rendered article HTML."""
    parser = SearchContentParser()
    parser.feed(html_content)
    parser.close()

    if parser.entries:
        return parser.entries

    text = re.sub(r"<br\s*/?>", "\n", html_content, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|h[1-6]|li|blockquote|pre|tr|ul|ol)>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    paragraphs = []
    for block in re.split(r"\n\s*\n+", text):
        cleaned = re.sub(r"\s+", " ", block).strip()
        if cleaned:
            paragraphs.append({"text": cleaned, "section_title": "", "section_anchor": ""})

    return paragraphs
