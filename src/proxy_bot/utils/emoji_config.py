from __future__ import annotations

import re
import tomllib
from pathlib import Path

import emoji as emoji_lib

# A config entry is either a "[tg_emoji:<id>:<shortcode>]" tag (from
# scripts/generate_emoji_pack.py) or a literal Unicode emoji override, e.g.
# `language = "🌐"` instead of a pack-backed custom emoji - both forms are
# valid message-text values, but only a tag carries an id an inline-keyboard
# button can use (see custom_emoji_id below).
_TAG_RE = re.compile(r"^\[tg_emoji:(\d+):([a-z0-9_+\-]+)\]$")

# Shortcodes that aren't real `emoji` package aliases, so `fallback_for`
# can't derive a fallback character from the name alone - needed here for
# utils/i18n.py's tag-expansion (the <tg-emoji> fallback shown to clients
# that can't render custom emoji). scripts/generate_emoji_pack.py needs the
# exact same table for the same reason (Telegram's
# createStickerSet/replaceSticker also reject a non-real-emoji "emoji"
# field) but keeps its own copy rather than importing this module - see
# that script's FALLBACK_OVERRIDES for why. Keep both in sync: add to this
# whenever a new shortcode in generate_emoji_pack.py:ICONS isn't a valid
# `:shortcode:` alias, or a literal ":name:" string leaks into rendered
# message text instead of a glyph.
FALLBACK_OVERRIDES: dict[str, str] = {
    "chevron_left": "◀️",
    "chevron_right": "▶️",
    "language": "🌐",
    "check": "✔️",
}


def fallback_for(shortcode: str) -> str:
    return FALLBACK_OVERRIDES.get(shortcode) or emoji_lib.emojize(f":{shortcode}:", language="alias")


def load_emoji_config(path: Path) -> dict[str, str]:
    """Read locales/emoji.toml's `[emoji]` table: shortcode -> tag or literal
    emoji. Missing file reads as empty rather than erroring, matching how a
    freshly checked-out repo with no pack generated yet should behave -
    every message referencing `{ $emoji_x }` would then render an empty
    string, same as any other unset Fluent variable."""
    if not path.exists():
        return {}
    with path.open("rb") as fp:
        return tomllib.load(fp).get("emoji", {})


def custom_emoji_id(value: str) -> str | None:
    """The numeric id inside a "[tg_emoji:<id>:<shortcode>]" tag, or None if
    `value` is a literal Unicode override - inline-keyboard buttons can only
    carry a real custom emoji id (Telegram's icon_custom_emoji_id field),
    never a literal character, so callers building button styles fall back
    to no icon in that case rather than erroring."""
    match = _TAG_RE.match(value)
    return match.group(1) if match else None


def plain_emoji(value: str) -> str:
    """The literal Unicode character(s) this config value should render as
    when custom emoji can't be shown at all - not just "no id", but nowhere
    to put one, e.g. Telegram callback-query popups (answerCallbackQuery's
    `text` is plain, unparsed - a pasted `<tg-emoji ...>` tag would show up
    as literal angle-bracket text instead of being rendered). A
    "[tg_emoji:...]" tag resolves to its own fallback character; a literal
    override is already plain and passes through unchanged."""
    match = _TAG_RE.match(value)
    if match is None:
        return value
    return fallback_for(match.group(2))


# Same syntax as _TAG_RE but unanchored, since this one hunts for the tag
# anywhere inside a larger string (a full rendered message, not a single
# config value) rather than validating that a whole string is just the tag.
_EMBEDDED_TAG_RE = re.compile(r"\[tg_emoji:(\d+):([a-z0-9_+\-]+)\]")


def expand_tags(text: str) -> str:
    """Replace every "[tg_emoji:<id>:<shortcode>]" marker in `text` with the
    real <tg-emoji emoji-id="..."> HTML entity. Used on a message's fully
    assembled text (utils/i18n.py: EmojiFluentCompileCore.get(), run after
    Fluent substitution so a marker reaches here whether it was written
    directly in a .ftl value or, like a link's bullet
    (utils/formatting.py), built in Python and substituted into a
    variable) - but also directly by any Python code that builds HTML
    outside that pipeline entirely (formatting.py again: its output is
    dropped straight into a Format() widget, which never touches Fluent at
    all) and still needs a real, already-expanded tag rather than a raw
    marker a client would show as literal text.
    """

    def _sub(match: re.Match[str]) -> str:
        emoji_id, fallback_name = match.group(1), match.group(2)
        fallback = fallback_for(fallback_name)
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

    return _EMBEDDED_TAG_RE.sub(_sub, text)


_TAG_HTML_RE = re.compile(r'<tg-emoji emoji-id="(\d+)">.*?</tg-emoji>')


def collapse_tags(text: str, registry: dict[str, str]) -> str:
    """A display-only cousin of expand_tags(), for the opposite direction:
    replace every real `<tg-emoji emoji-id="...">` entity in `text` whose id
    is a key in `registry` (id -> shortcode, e.g. dialogs.common.CUSTOM_EMOJI
    inverted) with a plain "[shortcode]" label - so an admin previewing raw
    HTML they're about to send (a <code> block, say) sees a name instead of
    a wall of numeric ids. An id `registry` doesn't recognize - someone
    else's custom emoji, forwarded content, a different pack entirely - has
    no shortcode to show, so it's left as the real tag rather than guessed
    at.

    Deliberately NOT the "[tg_emoji:<id>:<shortcode>]" marker syntax
    expand_tags() reads: this output is meant to be inert past this point,
    but a value on its way into an I18N-rendered message (e.g. interpolated
    as a Fluent variable) still passes through EmojiFluentCompileCore.get(),
    which runs expand_tags() (and emoji.emojize()) over its *entire* result
    - including already-substituted variables - so a real marker written
    here would just get expanded straight back into a live tag one step
    later, undoing the whole point of collapsing it.
    """

    def _sub(match: re.Match[str]) -> str:
        emoji_id = match.group(1)
        shortcode = registry.get(emoji_id)
        if shortcode is None:
            return match.group(0)
        return f"[{shortcode}]"

    return _TAG_HTML_RE.sub(_sub, text)
