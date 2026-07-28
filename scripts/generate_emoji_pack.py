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

# shortcode -> (Material Symbols "filled" icon name, color category)
# The shortcode is the existing :shortcode: alias already used throughout
# locales/*/bot.ftl (see utils/i18n.py: EmojiFluentCompileCore) - it doubles
# as the fallback glyph for clients that can't render custom emoji.
ICONS: dict[str, tuple[str, str]] = {
    "arrow_backward": ("arrow_back", "blue"),
    "bust_in_silhouette": ("person", "blue"),
    "chevron_left": ("chevron_left", "blue"),
    "chevron_right": ("chevron_right", "blue"),
    "clipboard": ("assignment", "blue"),
    "gear": ("settings", "blue"),
    "heavy_plus_sign": ("add", "blue"),
    "key": ("vpn_key", "blue"),
    "leftwards_arrow_with_hook": ("undo", "blue"),
    "link": ("link", "blue"),
    "loudspeaker": ("campaign", "blue"),
    "no_entry_sign": ("block", "red"),
    "package": ("inventory_2", "blue"),
    "pencil2": ("edit", "blue"),
    "question": ("help", "blue"),
    "shield": ("shield", "blue"),
    "small_blue_diamond": ("diamond", "blue"),
    "wastebasket": ("delete", "red"),
    "wave": ("waving_hand", "blue"),
    "white_check_mark": ("check_circle", "green"),
    "x": ("close", "red"),
}

# chevron_left/right aren't real :shortcode: emoji aliases (the `emoji`
# package has none), and Telegram's createStickerSet rejects an item whose
# "emoji" field isn't an actual emoji character - so these two need an
# explicit fallback instead of being emojized from their own name.
FALLBACK_OVERRIDES = {
    "chevron_left": "◀️",
    "chevron_right": "▶️",
}

COLORS = {
    "blue": "#3B82F6",
    "green": "#22C55E",
    "red": "#EF4444",
}

MATERIAL_ICON_URL = "https://cdn.jsdelivr.net/npm/@material-design-icons/svg@latest/filled/{name}.svg"

# No background badge - a colored square behind the glyph read as visibly
# taller/heavier than surrounding text and made the icon itself harder to
# read at a glance. Just the glyph, in its category color, on a transparent
# canvas - closer to how a normal colored Unicode emoji sits in text.
CANVAS = 100
ICON_SIZE = 64

DEFAULT_TITLE = "LPR Proxy Bot Icons"
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


def build_badge_pngs(work_dir: Path) -> dict[str, Path]:
    pngs = {}
    for shortcode, (material_name, color_key) in ICONS.items():
        icon_svg = fetch_icon_svg(material_name)
        badge_svg = build_badge_svg(icon_svg, COLORS[color_key])
        svg_path = work_dir / f"{shortcode}.svg"
        png_path = work_dir / f"{shortcode}.png"
        svg_path.write_text(badge_svg)
        svg_to_png(svg_path, png_path)
        pngs[shortcode] = png_path
        print(f"built {shortcode} <- {material_name} ({color_key})")
    return pngs


async def upload_pack(pngs: dict[str, Path], title: str, short_name: str, recreate: bool) -> dict[str, str]:
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
        fallback = FALLBACK_OVERRIDES.get(shortcode) or emoji_lib.emojize(f":{shortcode}:", language="alias")
        uploaded = await client.upload_file(str(png_path))
        media = types.InputMediaUploadedDocument(
            file=uploaded,
            mime_type="image/png",
            attributes=[types.DocumentAttributeFilename(file_name=f"{shortcode}.png")],
        )
        result = await client(functions.messages.UploadMediaRequest(peer=types.InputPeerSelf(), media=media))
        doc = result.document
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--short-name", default=DEFAULT_SHORT_NAME)
    parser.add_argument("--recreate", action="store_true", help="delete an existing set with the same short name first")
    args = parser.parse_args()

    for var in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH"):
        if var not in os.environ:
            sys.exit(f"{var} is not set - get one at https://my.telegram.org and export it.")

    with tempfile.TemporaryDirectory() as tmp:
        pngs = build_badge_pngs(Path(tmp))
        mapping = asyncio.run(upload_pack(pngs, args.title, args.short_name, args.recreate))

    print("\n# For message text - paste into locales/*/bot.ftl:")
    for shortcode, doc_id in mapping.items():
        print(f"[tg_emoji:{doc_id}:{shortcode}]")

    print("\n# For inline keyboard buttons - paste into dialogs/common.py: CUSTOM_EMOJI:")
    for shortcode, doc_id in mapping.items():
        print(f'    "{shortcode}": "{doc_id}",')


if __name__ == "__main__":
    main()
