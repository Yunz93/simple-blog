"""Shared helper functions for build-time parsing and normalization."""

from __future__ import annotations

import html
import re
from datetime import UTC, date as date_cls, datetime


def xml_10_safe_text(value: str) -> str:
    """Remove code points illegal in XML 1.0 text."""
    if not value:
        return value or ""

    out = []
    for ch in value:
        codepoint = ord(ch)
        if codepoint < 0x20 and codepoint not in (0x9, 0xA, 0xD):
            continue
        if 0xD800 <= codepoint <= 0xDFFF:
            continue
        if codepoint in (0xFFFE, 0xFFFF):
            continue
        out.append(ch)
    return "".join(out)


def atom_text(value: str) -> str:
    return html.escape(xml_10_safe_text(value))


def resolve_frontmatter_value(frontmatter, key, fallback):
    """Read a frontmatter field and fall back when the value is empty."""
    value = frontmatter.get(key)
    if value is None:
        return fallback
    if isinstance(value, str) and not value.strip():
        return fallback
    if isinstance(value, list) and not value:
        return fallback
    return value


def normalize_datetime(value: datetime) -> datetime:
    """Normalize datetimes so sort keys never mix aware and naive instances."""
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def parse_timestamp_value(value):
    """Parse frontmatter timestamps from common markdown-press / Obsidian formats."""
    if value is None:
        return None

    if isinstance(value, datetime):
        return normalize_datetime(value)

    if isinstance(value, date_cls):
        return datetime.combine(value, datetime.min.time())

    text = str(value).strip()
    if not text:
        return None

    try:
        return normalize_datetime(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%d %a %H:%M:%S",
        "%Y-%m-%d %A %H:%M:%S",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    match = re.match(r"^(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}:\d{2}))?", text)
    if match:
        if match.group(2):
            return datetime.strptime(f"{match.group(1)} {match.group(2)}", "%Y-%m-%d %H:%M:%S")
        return datetime.strptime(match.group(1), "%Y-%m-%d")

    obsidian_match = re.search(
        r"(\d{4}-\d{2}-\d{2})\s+\S+\s+(\d{1,2}:\d{2}:\d{2})",
        text,
    )
    if obsidian_match:
        try:
            return datetime.strptime(
                f"{obsidian_match.group(1)} {obsidian_match.group(2)}",
                "%Y-%m-%d %H:%M:%S",
            )
        except ValueError:
            return None

    return None


def slugify(text) -> str:
    """Convert text into a URL-safe slug."""
    text = str(text).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")
