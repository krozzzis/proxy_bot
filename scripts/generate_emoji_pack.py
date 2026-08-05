#!/usr/bin/env python3
"""Build the bot's custom-emoji icon pack from Material Symbols and upload it
to Telegram as a custom emoji sticker set owned by a user account.

Bots can't create sticker sets themselves - custom emoji packs need a
Premium user account as the owner (Bot API only *references* existing
custom emoji by id). This script logs in with Telethon as that user,
uploads one badge PNG per icon, and writes the resulting document ids
straight into locales/emoji.toml - the single source both wiring points
below read from, so there's nothing left to hand-paste anywhere.

Two distinct wiring points use those ids, and they are not interchangeable:
- Message text (window titles, prompts): a `{ $emoji_<shortcode> }` Fluent
  variable in the .ftl locale files, injected automatically from
  emoji.toml on every render (EmojiFluentCompileCore, utils/i18n.py) and
  expanded into a `<tg-emoji emoji-id="...">` entity - text entities only
  apply to message bodies, not button captions.
- Inline keyboard buttons: the dedicated `icon_custom_emoji_id`/`style`
  fields on InlineKeyboardButton (aiogram_dialog: `Style(emoji_id=...,
  style=ButtonStyle.PRIMARY)`, see dialogs/common.py: CUSTOM_EMOJI, also
  read from emoji.toml - but only entries that are still a
  `[tg_emoji:...]` tag get a usable id there; a literal Unicode override
  can't back a button icon). Button label text stays a plain string with
  no :shortcode: prefix - clients that predate this field just show the
  button with no icon.

Requirements (not part of the bot's own runtime dependencies):
    - `rsvg-convert` (nix: `librsvg`, debian: `librsvg2-bin`) on PATH.
    - `telethon`, installed via the `emoji-pack` dependency group:
          uv run --group emoji-pack scripts/generate_emoji_pack.py

Environment:
    TELEGRAM_API_ID / TELEGRAM_API_HASH - from https://my.telegram.org.
    TELEGRAM_SESSION - Telethon session file path (default: ./emoji_pack).

Usage:
    uv run --group emoji-pack scripts/generate_emoji_pack.py --add-missing
    uv run --group emoji-pack scripts/generate_emoji_pack.py --recreate
    uv run --group emoji-pack scripts/generate_emoji_pack.py   # replace in place

Three modes, pick the narrowest one that covers what changed in ICONS:
- (no flag) replace_pack: swaps each existing sticker's *image* in place,
  keeping every id. Only works if ICONS' size still matches the live set's -
  it can't add or remove icons, only re-render ones already there.
- --add-missing: appends new ICONS entries to the live set without touching
  anything already uploaded - existing ids don't change, so you only need to
  paste the newly printed ones. This is the one to reach for after adding a
  shortcode to ICONS (as opposed to editing an existing icon's Material name
  or color).
- --recreate: deletes the existing set *before* uploading a fresh one
  (Telegram won't let you create a set under a short_name that's still in
  use, so there's no way to upload-then-swap). Every id rotates, not just
  changed ones - reach for this only when you need to reorder or remove
  icons, not to add one. If a run fails partway - as StickerEmojiInvalidError
  once did here, from an icon whose shortcode isn't a real emoji alias - the
  pack is left deleted and locales/emoji.toml's ids are dangling. Re-run (no
  --recreate needed, there's nothing left to delete) to fix it - the write
  step below is idempotent.

Any entry in emoji.toml that's already a literal Unicode override (not a
`[tg_emoji:...]` tag) is left alone on write, in every mode - a manual
`language = "🌐"` survives a `--recreate` same as anything else.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
from pathlib import Path

import emoji as emoji_lib
import tomli_w

# shortcode -> Material Symbols "filled" icon name.
# The shortcode is the existing :shortcode: alias already used throughout
# locales/*/bot.ftl (see utils/i18n.py: EmojiFluentCompileCore) - it doubles
# as the fallback glyph for clients that can't render custom emoji.
ICONS: dict[str, str] = {
    "arrow_backward": "arrow_back",
    "bar_chart": "data_usage",
    "bust_in_silhouette": "person",
    "calendar": "calendar_month",
    "check": "check",
    "chevron_left": "chevron_left",
    "chevron_right": "chevron_right",
    "clipboard": "assignment",
    "gear": "settings",
    "heavy_plus_sign": "add",
    "infinity": "all_inclusive",
    "key": "vpn_key",
    "language": "translate",
    "leftwards_arrow_with_hook": "undo",
    "link": "link",
    "loudspeaker": "campaign",
    "no_entry_sign": "block",
    "package": "inventory_2",
    "pencil2": "edit",
    "question": "help",
    "shield": "shield",
    "small_blue_diamond": "diamond",
    "wastebasket": "delete",
    "wave": "waving_hand",
    "white_check_mark": "check_circle",
    "x": "close",
}

# chevron_left/right/language/check aren't real :shortcode: emoji aliases
# (the `emoji` package has none), and Telegram's
# createStickerSet/replaceSticker rejects an item whose "emoji" field isn't
# an actual emoji character - so these need an explicit fallback instead of
# being emojized from their own name.
#
# Kept in sync by hand with utils/emoji_config.py's identical
# FALLBACK_OVERRIDES (the bot's own <tg-emoji> fallback needs the exact same
# table, for the exact same reason - a shortcode here with no override there
# renders as a literal ":shortcode:" string in message text instead of a
# glyph, since that side has no reachable network to re-derive one from).
# Not imported from there on purpose: importing anything under `proxy_bot`
# runs proxy_bot/__init__.py, which pulls in the full bot stack (aiogram,
# aiogram-dialog, redis, ...) - dependencies this script deliberately
# doesn't require (see module docstring).
FALLBACK_OVERRIDES = {
    "chevron_left": "◀️",
    "chevron_right": "▶️",
    "language": "🌐",
    "check": "✔️",
}

# Plain white, no per-category color: a colored icon on a same-colored
# ButtonStyle (DANGER/SUCCESS) background was nearly invisible, and picking
# per-usage colors (colored in text, white on colored buttons) would need
# two variants of every icon in the pack. One white glyph everywhere is the
# simple trade-off the icons were asked for - message-text use on a light
# background is the one place this may read poorly; worth a look live.
ICON_COLOR = "#FFFFFF"

MATERIAL_ICON_URL = "https://cdn.jsdelivr.net/npm/@material-design-icons/svg@latest/filled/{name}.svg"

# No background badge - a colored square behind the glyph read as visibly
# taller/heavier than surrounding text and made the icon itself harder to
# read at a glance. Just the glyph on a transparent canvas - closer to how
# a normal Unicode emoji sits in text.
CANVAS = 100
ICON_SIZE = 64

DEFAULT_TITLE = "Proxy Bot Icons"
DEFAULT_SHORT_NAME = "lprproxy_icons"

# Single source of truth for both wiring points - see utils/emoji_config.py
# and dialogs/common.py: CUSTOM_EMOJI on the reading side.
EMOJI_CONFIG_PATH = Path(__file__).resolve().parent.parent / "locales" / "emoji.toml"
_TAG_RE = re.compile(r"^\[tg_emoji:\d+:[a-z0-9_+\-]+\]$")


def fetch_icon_svg(material_name: str) -> str:
    url = MATERIAL_ICON_URL.format(name=material_name)
    with urllib.request.urlopen(url) as resp:  # noqa: S310 - fixed jsdelivr host
        return resp.read().decode("utf-8")


def build_badge_svg(icon_svg: str, color: str) -> str:
    inner = re.search(r"<svg[^>]*>(.*)</svg>", icon_svg, re.S).group(1).strip()
    icon_offset = (CANVAS - ICON_SIZE) / 2
    icon_scale = ICON_SIZE / 24
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS}" height="{CANVAS}" viewBox="0 0 {CANVAS} {CANVAS}">
  <g transform="translate({icon_offset:.3f},{icon_offset:.3f}) scale({icon_scale:.5f})" fill="{color}">
    {inner}
  </g>
</svg>
"""


def svg_to_png(svg_path: Path, png_path: Path) -> None:
    try:
        subprocess.run(
            ["rsvg-convert", "-w", str(CANVAS), "-h", str(CANVAS), "--keep-aspect-ratio", "-o", str(png_path), str(svg_path)],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        sys.exit("rsvg-convert not found on PATH - install librsvg (nix: `nix-shell -p librsvg`) and retry.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"rsvg-convert failed for {svg_path}: {e.stderr.decode(errors='replace')}")


def build_badge_pngs(work_dir: Path, shortcodes: list[str]) -> dict[str, Path]:
    pngs = {}
    for shortcode in shortcodes:
        material_name = ICONS[shortcode]
        icon_svg = fetch_icon_svg(material_name)
        badge_svg = build_badge_svg(icon_svg, ICON_COLOR)
        svg_path = work_dir / f"{shortcode}.svg"
        png_path = work_dir / f"{shortcode}.png"
        svg_path.write_text(badge_svg)
        svg_to_png(svg_path, png_path)
        pngs[shortcode] = png_path
        print(f"built {shortcode} <- {material_name}")
    return pngs


def _fallback_for(shortcode: str) -> str:
    return FALLBACK_OVERRIDES.get(shortcode) or emoji_lib.emojize(f":{shortcode}:", language="alias")


def _stripped(text: str) -> str:
    """Telegram drops the U+FE0F "emoji presentation" variation selector
    from a sticker's `emoticon` before storing it, so a fallback generated
    locally (which keeps it) never string-equals what GetStickerSet hands
    back for the same glyph - strip it from both sides before comparing."""
    return text.replace("\ufe0f", "").replace("\ufe0e", "")


async def _upload_document(client, png_path: Path, shortcode: str):
    from telethon.tl import functions, types

    uploaded = await client.upload_file(str(png_path))
    media = types.InputMediaUploadedDocument(
        file=uploaded,
        mime_type="image/png",
        attributes=[types.DocumentAttributeFilename(file_name=f"{shortcode}.png")],
    )
    result = await client(functions.messages.UploadMediaRequest(peer=types.InputPeerSelf(), media=media))
    return result.document


async def create_pack(pngs: dict[str, Path], title: str, short_name: str, recreate: bool) -> dict[str, str]:
    """Delete the existing set (if --recreate) and create a fresh one. Every
    document gets a new id, whether or not the set existed before - use
    replace_pack() instead to edit an existing set's icons in place."""
    from telethon import TelegramClient
    from telethon.errors import RPCError
    from telethon.tl import functions, types

    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    session = os.environ.get("TELEGRAM_SESSION", "emoji_pack")

    client = TelegramClient(session, api_id, api_hash)
    await client.start()

    if recreate:
        try:
            await client(functions.stickers.DeleteStickerSetRequest(stickerset=types.InputStickerSetShortName(short_name=short_name)))
            print(f"deleted existing set {short_name!r}")
        except RPCError as e:
            print(f"(nothing to delete, or delete failed: {e})")

    items = []
    order = []
    for shortcode, png_path in pngs.items():
        fallback = _fallback_for(shortcode)
        doc = await _upload_document(client, png_path, shortcode)
        input_doc = types.InputDocument(id=doc.id, access_hash=doc.access_hash, file_reference=doc.file_reference)
        items.append(types.InputStickerSetItem(document=input_doc, emoji=fallback))
        order.append(shortcode)
        print(f"uploaded {shortcode} (fallback {fallback})")

    result = await client(
        functions.stickers.CreateStickerSetRequest(
            user_id=types.InputUserSelf(),
            title=title,
            short_name=short_name,
            stickers=items,
            emojis=True,
        )
    )
    docs = getattr(result, "documents", None) or result.set.documents
    await client.disconnect()
    return {shortcode: str(doc.id) for shortcode, doc in zip(order, docs)}


async def replace_pack(pngs: dict[str, Path], title: str, short_name: str) -> dict[str, str]:
    """Edit the existing set's icons in place: rename it if the title
    changed, and swap each sticker's image for a freshly rendered one via
    ReplaceStickerRequest, rather than deleting and recreating the set.

    Telegram sticker items carry no name of their own (just an emoji
    fallback and a file), so matching "this uploaded document is the gear
    icon" relies on position - the existing set's documents, in order, are
    expected to correspond 1:1 to ICONS in dict order. That only holds if
    the set was last built by this same script; a set edited some other
    way, or with items added/removed out of band, would produce a wrong
    (but otherwise silent) swap. GetStickerSet's `packs` field maps each
    document id back to the emoji it was uploaded with, so every position
    is cross-checked against the fallback this script would generate for
    the shortcode expected there, and the whole run aborts on the first
    mismatch rather than replace blind.
    """
    from telethon import TelegramClient
    from telethon.tl import functions, types

    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    session = os.environ.get("TELEGRAM_SESSION", "emoji_pack")

    client = TelegramClient(session, api_id, api_hash)
    await client.start()

    input_set = types.InputStickerSetShortName(short_name=short_name)
    current = await client(functions.messages.GetStickerSetRequest(stickerset=input_set, hash=0))

    if current.set.title != title:
        await client(functions.stickers.RenameStickerSetRequest(stickerset=input_set, title=title))
        print(f"renamed set {current.set.title!r} -> {title!r}")

    shortcodes = list(pngs.keys())
    if len(current.documents) != len(shortcodes):
        sys.exit(
            f"Existing set {short_name!r} has {len(current.documents)} stickers, "
            f"but {len(shortcodes)} are defined in ICONS - counts must match to replace by "
            f"position. Use --recreate for a fresh set instead."
        )

    doc_id_to_emoji = {doc_id: pack.emoticon for pack in current.packs for doc_id in pack.documents}

    mapping = {}
    for shortcode, old_doc in zip(shortcodes, current.documents):
        fallback = _fallback_for(shortcode)
        live_emoji = doc_id_to_emoji.get(old_doc.id)
        if live_emoji is not None and live_emoji not in fallback and fallback not in live_emoji:
            sys.exit(
                f"Position mismatch: expected {shortcode!r} (fallback {fallback}) at this slot, "
                f"but the live document there is tagged {live_emoji!r}. The set's item order no "
                f"longer matches ICONS - aborting before replacing the wrong icon. Use --recreate "
                f"for a fresh set instead."
            )
        png_path = pngs[shortcode]
        new_doc = await _upload_document(client, png_path, shortcode)
        new_input_doc = types.InputDocument(id=new_doc.id, access_hash=new_doc.access_hash, file_reference=new_doc.file_reference)
        old_input_doc = types.InputDocument(id=old_doc.id, access_hash=old_doc.access_hash, file_reference=old_doc.file_reference)
        item = types.InputStickerSetItem(document=new_input_doc, emoji=fallback)
        await client(functions.stickers.ReplaceStickerRequest(sticker=old_input_doc, new_sticker=item))
        print(f"replaced {shortcode} (fallback {fallback})")

    # ReplaceStickerRequest's own response document id is *not* the set's
    # final committed id (confirmed the hard way: a prior run recorded ids
    # straight off it, and every one of them turned out to be a stale
    # staging id once the set was re-fetched) - re-fetch after all
    # replacements to read back what Telegram actually kept.
    final = await client(functions.messages.GetStickerSetRequest(stickerset=input_set, hash=0))
    mapping = {shortcode: str(doc.id) for shortcode, doc in zip(shortcodes, final.documents)}

    await client.disconnect()
    return mapping


async def add_missing_icons(work_dir: Path, title: str, short_name: str) -> dict[str, str]:
    """Append whatever's in ICONS but not yet in the live set, leaving every
    existing sticker (and its id) untouched - unlike replace_pack (which
    demands an exact size match and replaces by position) or --recreate
    (which deletes and rebuilds the whole set, rotating *every* id just to
    add one icon). This is the point-edit path: "I added a shortcode to
    ICONS, ship just that."

    "Missing" is decided by fallback emoji, not position: each shortcode's
    `_fallback_for()` value is checked against the live set's per-document
    emoji (GetStickerSet's `packs[].emoticon`), so this works no matter
    where in ICONS' dict order the new keys were inserted - AddStickerToSet
    can only append at the end, so after this runs once, live document
    order no longer matches ICONS' order anyway (replace_pack's position
    trick stops applying and it'll refuse to run - use --recreate at that
    point if in-place replacement of an existing icon's image is needed).

    Two wrinkles found the hard way (an early version of this compared raw
    strings and re-uploaded 9 icons that were already there):
    - Telegram strips the U+FE0F variation selector from `emoticon` before
      storing it, but `emoji.emojize()` includes it (e.g. "✔️" vs
      the "✔" Telegram hands back) - comparisons go through
      `_stripped()` on both sides.
    - Two shortcodes can legitimately share one fallback glyph (e.g.
      "arrow_backward" and "chevron_left" are both "◀️") - a live set has
      one live document per occurrence, so presence is tracked by *count*
      per stripped glyph, consumed in ICONS' iteration order, rather than a
      plain set membership check that can't tell "0 of 2 uploaded" from "2
      of 2 uploaded".
    """
    from collections import Counter

    from telethon import TelegramClient
    from telethon.tl import functions, types

    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    session = os.environ.get("TELEGRAM_SESSION", "emoji_pack")

    client = TelegramClient(session, api_id, api_hash)
    await client.start()

    input_set = types.InputStickerSetShortName(short_name=short_name)
    current = await client(functions.messages.GetStickerSetRequest(stickerset=input_set, hash=0))

    if current.set.title != title:
        await client(functions.stickers.RenameStickerSetRequest(stickerset=input_set, title=title))
        print(f"renamed set {current.set.title!r} -> {title!r}")

    existing_counts = Counter()
    for pack in current.packs:
        existing_counts[pack.emoticon] += len(pack.documents)

    seen_counts = Counter()
    missing = []
    for code in ICONS:
        key = _stripped(_fallback_for(code))
        seen_counts[key] += 1
        if seen_counts[key] > existing_counts[key]:
            missing.append(code)
    if not missing:
        print("Nothing to add - every icon in ICONS already has a matching sticker in the live set.")
        await client.disconnect()
        return {}

    pngs = build_badge_pngs(work_dir, missing)
    before_count = len(current.documents)
    for shortcode in missing:
        fallback = _fallback_for(shortcode)
        new_doc = await _upload_document(client, pngs[shortcode], shortcode)
        input_doc = types.InputDocument(id=new_doc.id, access_hash=new_doc.access_hash, file_reference=new_doc.file_reference)
        item = types.InputStickerSetItem(document=input_doc, emoji=fallback)
        await client(functions.stickers.AddStickerToSetRequest(stickerset=input_set, sticker=item))
        print(f"added {shortcode} (fallback {fallback})")

    # Same rationale as replace_pack: re-fetch rather than trust the
    # per-call response id. AddStickerToSet always appends, so the new
    # entries are reliably the tail of the refreshed document list, in the
    # order they were added - no fallback-matching ambiguity needed here.
    final = await client(functions.messages.GetStickerSetRequest(stickerset=input_set, hash=0))
    new_docs = final.documents[before_count:]
    mapping = {shortcode: str(doc.id) for shortcode, doc in zip(missing, new_docs)}

    await client.disconnect()
    return mapping


def update_emoji_config(path: Path, mapping: dict[str, str]) -> None:
    """Merge freshly minted ids into locales/emoji.toml. Any shortcode
    already holding a literal Unicode override (not a `[tg_emoji:...]` tag)
    is left untouched - this is what makes a manual `language = "🌐"`
    survive a re-run of any mode, --recreate included. Existing key order
    is preserved; genuinely new shortcodes are appended in ICONS order."""
    existing: dict[str, str] = {}
    if path.exists():
        with path.open("rb") as fp:
            existing = tomllib.load(fp).get("emoji", {})

    merged = dict(existing)
    written, kept_overrides = [], []
    for shortcode, doc_id in mapping.items():
        if shortcode in existing and not _TAG_RE.match(existing[shortcode]):
            kept_overrides.append(shortcode)
            continue
        merged[shortcode] = f"[tg_emoji:{doc_id}:{shortcode}]"
        written.append(shortcode)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fp:
        tomli_w.dump({"emoji": merged}, fp)

    print(f"\nWrote {len(written)} id(s) to {path}")
    if kept_overrides:
        print(f"Kept existing literal override for: {', '.join(kept_overrides)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--short-name", default=DEFAULT_SHORT_NAME)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--recreate",
        action="store_true",
        help="delete the existing set and create a fresh one - rotates every id, not just changed ones",
    )
    mode.add_argument(
        "--add-missing",
        action="store_true",
        help="append icons that are in ICONS but not in the live set yet, leaving existing ones untouched",
    )
    args = parser.parse_args()

    for var in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH"):
        if var not in os.environ:
            sys.exit(f"{var} is not set - get one at https://my.telegram.org and export it.")

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        if args.add_missing:
            mapping = asyncio.run(add_missing_icons(work_dir, args.title, args.short_name))
        else:
            pngs = build_badge_pngs(work_dir, list(ICONS.keys()))
            if args.recreate:
                mapping = asyncio.run(create_pack(pngs, args.title, args.short_name, recreate=True))
            else:
                mapping = asyncio.run(replace_pack(pngs, args.title, args.short_name))

    if not mapping:
        return

    update_emoji_config(EMOJI_CONFIG_PATH, mapping)


if __name__ == "__main__":
    main()
