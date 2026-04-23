"""Simple Blog builder package."""

__all__ = ["BlogBuilder"]


def __getattr__(name):
    if name == "BlogBuilder":
        from .builder import BlogBuilder

        return BlogBuilder
    raise AttributeError(name)
