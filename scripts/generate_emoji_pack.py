#!/usr/bin/env python3
"""Build the bot's custom-emoji icon pack from Material Symbols and upload it
to Telegram as a custom emoji sticker set owned by a user account.

Bots can't create sticker sets themselves - custom emoji packs need a
Premium user account as the owner (Bot API only *references* existing
custom emoji by id). This script logs in with Telethon as that user,
uploads one badge PNG per icon, and prints the resulting document ids.

Two distinct wiring points use those ids, and they are not interchangeable:
- Message text (window titles, prompts): `[tg_emoji:<id>:<shortcode>]` in
  the .ftl locale files, expanded by EmojiFluentCompileCore (utils/i18n.py)
  into a `<tg-emoji emoji-id="...">` entity - text entities only apply to
  message bodies, not button captions.
- Inline keyboard buttons: the dedicated `icon_custom_emoji_id`/`style`
  fields on InlineKeyboardButton (aiogram_dialog: `Style(emoji_id=...,
  style=ButtonStyle.PRIMARY)`, see dialogs/common.py: CUSTOM_EMOJI). Button
  label text stays a plain string with no :shortcode: prefix - clients that
  predate this field just show the button with no icon.

Requirements (not part of the bot's own runtime dependencies):
    - `rsvg-convert` (nix: `librsvg`, debian: `librsvg2-bin`) on PATH.
    - `telethon`, installed via the `emoji-pack` dependency group:
          uv run --group emoji-pack scripts/generate_emoji_pack.py

Environment:
    TELEGRAM_API_ID / TELEGRAM_API_HASH - from https://my.telegram.org.
    TELEGRAM_SESSION - Telethon session file path (default: ./emoji_pack).

Usage:
    uv run --group emoji-pack scripts/generate_emoji_pack.py --recreate

--recreate deletes the existing set *before* uploading the new one (Telegram
won't let you create a set under a short_name that's still in use, so there's
no way to upload-then-swap). If a run fails partway - as
StickerEmojiInvalidError once did here, from an icon whose shortcode isn't a
real emoji alias - the pack is left deleted and every id in CUSTOM_EMOJI and
the .ftl files is dangling. Re-run (no --recreate needed, there's nothing
left to delete) and copy the freshly printed ids over the old ones in both
places before considering the job done.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import emoji as emoji_lib

# shortcode -> Material Symbols "filled" icon name.
# The shortcode is the existing :shortcode: alias already used throughout
# locales/*/bot.ftl (see utils/i18n.py: EmojiFluentCompileCore) - it doubles
# as the fallback glyph for clients that can't render custom emoji.
ICONS: dict[str, str] = {
    "arrow_backward": "arrow_back",
    "bust_in_silhouette": "person",
    "chevron_left": "chevron_left",
    "chevron_right": "chevron_right",
    "clipboard": "assignment",
    "gear": "settings",
    "heavy_plus_sign": "add",
    "key": "vpn_key",
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

# chevron_left/right aren't real :shortcode: emoji aliases (the `emoji`
# package has none), and Telegram's createStickerSet/replaceSticker rejects
# an item whose "emoji" field isn't an actual emoji character - so these two
# need an explicit fallback instead of being emojized from their own name.
FALLBACK_OVERRIDES = {
    "chevron_left": "◀️",
    "chevron_right": "▶️",
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--short-name", default=DEFAULT_SHORT_NAME)
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="delete the existing set and create a fresh one, instead of editing it in place",
    )
    args = parser.parse_args()

    for var in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH"):
        if var not in os.environ:
            sys.exit(f"{var} is not set - get one at https://my.telegram.org and export it.")

    with tempfile.TemporaryDirectory() as tmp:
        pngs = build_badge_pngs(Path(tmp), list(ICONS.keys()))
        if args.recreate:
            mapping = asyncio.run(create_pack(pngs, args.title, args.short_name, recreate=True))
        else:
            mapping = asyncio.run(replace_pack(pngs, args.title, args.short_name))

    print("\n# For message text - paste into locales/*/bot.ftl:")
    for shortcode, doc_id in mapping.items():
        print(f"[tg_emoji:{doc_id}:{shortcode}]")

    print("\n# For inline keyboard buttons - paste into dialogs/common.py: CUSTOM_EMOJI:")
    for shortcode, doc_id in mapping.items():
        print(f'    "{shortcode}": "{doc_id}",')


if __name__ == "__main__":
    main()
