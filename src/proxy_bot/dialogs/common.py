from aiogram.types import Message
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.style.base import ButtonStyle, Style


def not_a_command(message: Message) -> bool:
    """TextInput filter: reject slash-commands so they fall through to command handlers."""
    return not (message.text or "").startswith("/")


# Custom-emoji document ids from the bot's Material Symbols icon pack
# (scripts/generate_emoji_pack.py). Telegram inline buttons carry these via
# a dedicated icon_custom_emoji_id field, not via text entities, so button
# label text stays a plain string with no :shortcode: prefix. Regenerating
# the pack rotates every id here.
CUSTOM_EMOJI = {
    "arrow_backward": "5422814592554280129",
    "bust_in_silhouette": "5424676319143174198",
    "gear": "5422765402293839322",
    "heavy_plus_sign": "5425076957987513993",
    "key": "5425059460290748236",
    "leftwards_arrow_with_hook": "5422698065796569264",
    "loudspeaker": "5425041283989154189",
    "no_entry_sign": "5424849539469189027",
    "package": "5422753565363971729",
    "pencil2": "5422543180685945933",
    "question": "5422644765252429636",
    "shield": "5424784870146611833",
    "wastebasket": "5424924383569292400",
    "white_check_mark": "5422716177673659074",
    "x": "5424999841849712198",
}


def icon(name: str, color: ButtonStyle | None = None, when: WhenCondition = None) -> Style:
    """Button style carrying a pack icon and, for confirm/cancel-type actions
    only, an accent color - plain navigation buttons stay icon-only so color
    reads as a deliberate signal rather than decoration. `icon(a, when=X) |
    icon(b, when=~X)` picks whichever alternative's condition matches."""
    return Style(style=color, emoji_id=CUSTOM_EMOJI[name], when=when)
