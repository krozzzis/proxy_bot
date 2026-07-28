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
    "arrow_backward": "5422795535784388529",
    "bust_in_silhouette": "5424728356966933997",
    "chevron_left": "5424704180596024830",
    "chevron_right": "5425123721591435717",
    "gear": "5422836015851151216",
    "heavy_plus_sign": "5424912142912498968",
    "key": "5422546651019517877",
    "leftwards_arrow_with_hook": "5424694031588303824",
    "loudspeaker": "5422893770276381417",
    "no_entry_sign": "5424811928440577113",
    "package": "5422519678624899490",
    "pencil2": "5422736930955633489",
    "question": "5424788606768163410",
    "shield": "5422465824029978096",
    "wastebasket": "5425141653079891359",
    "white_check_mark": "5425143379656744388",
    "x": "5422801295335533381",
}


def paginated_title(i18n, title: str, page: int, total_pages: int) -> str:
    """Append a "· page/total" suffix, but only once there's more than one
    page - a lone "(1/1)" next to a count that already says there's just
    one item is redundant noise, not information."""
    if total_pages <= 1:
        return title
    return f"{title} {i18n.get('admin-page-indicator', page=page + 1, total=total_pages)}"


def icon(name: str, color: ButtonStyle | None = None, when: WhenCondition = None) -> Style:
    """Button style carrying a pack icon and, for confirm/cancel-type actions
    only, an accent color - plain navigation buttons stay icon-only so color
    reads as a deliberate signal rather than decoration. `icon(a, when=X) |
    icon(b, when=~X)` picks whichever alternative's condition matches."""
    return Style(style=color, emoji_id=CUSTOM_EMOJI[name], when=when)
