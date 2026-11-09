# Copyright (c) 2025-2026 Zensical and contributors

# SPDX-License-Identifier: MIT
# All contributions are certified under the DCO

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from markdown import Extension, Markdown

from zensical.compat.mkdocstrings import get_mkdocstrings_extension
from zensical.extensions.context import ContextPreprocessor

if TYPE_CHECKING:
    from markdown import Markdown


# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------


class MkdocstringsExtension(Extension):
    """Markdown extension that renders Python API documentation."""

    name = "zensical.extensions.mkdocstrings"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the extension."""
        self._enabled: bool = kwargs.pop("enabled", True)
        self._kwargs = kwargs

    def extendMarkdown(self, md: Markdown) -> None:
        """Register Markdown extension."""
        if not self._enabled:
            return
        # The context extension must have registered its dummy processor
        # by then. We ensure this in `render()` by inserting it first
        # in the list of extension so that Python-Markdown calls its
        # `extendMarkdown()` method first.
        if context := ContextPreprocessor.from_markdown(md):
            config = context.config
            # We need the following indirection because we have
            # to pass the configured Markdown extensions again
            # to the actual extension.
            ext = get_mkdocstrings_extension(**self._kwargs, config=config)
            ext.extendMarkdown(md)


# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------


def makeExtension(**kwargs: Any) -> MkdocstringsExtension:
    """Register Markdown extension."""
    return MkdocstringsExtension(**kwargs)
