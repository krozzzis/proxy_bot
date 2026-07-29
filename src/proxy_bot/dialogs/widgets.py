from __future__ import annotations

from typing import Any

from aiogram_dialog.api.protocols import DialogManager
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.text import Text


class I18N(Text):
    """Like `Format`, but the template comes from Fluent instead of a
    literal string: `key` is looked up through the `i18n` core and its
    `{ $var }` placeholders are filled from window data, instead of a
    Python-side `.format()` pass over an already-rendered string.

    `key` itself is resolved against the data via `str.format_map` first
    (so `I18N("{banner}")` can pick a message id stored under the
    `banner` field, the same way a child dialog hands back a result), then
    every entry in `data` is passed to Fluent as a named argument - a
    getter whose dict keys already match the message's `{ $var }` names
    needs no further wiring. `**kwargs` overlay on top for cases the plain
    dict can't reach: a Select/List item lives under `data["item"]`, so its
    fields must be re-mapped explicitly (`code="{item[code]}"`), same
    dotted/bracket syntax `Format` uses.
    """

    def __init__(self, key: str, when: WhenCondition = None, **kwargs: Any):
        super().__init__(when=when)
        self.key = key
        self.kwargs = kwargs

    async def _render_text(self, data: dict, manager: DialogManager) -> str:
        i18n = manager.middleware_data["i18n"]
        key = self.key.format_map(data)
        args = dict(data)
        for name, value in self.kwargs.items():
            args[name] = value.format_map(data) if isinstance(value, str) else value
        return i18n.get(key, **args)
