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
    "arrow_backward": "5425102109315998423",
    "bust_in_silhouette": "5422406733869920062",
    "chevron_left": "5422495390584840531",
    "chevron_right": "5424619011394544688",
    "gear": "5424814720169322177",
    "heavy_plus_sign": "5425053778049016028",
    "key": "5424947786846085477",
    "leftwards_arrow_with_hook": "5422638632039127619",
    "loudspeaker": "5422785094718894954",
    "no_entry_sign": "5424910789997797782",
    "package": "5425024619516044042",
    "pencil2": "5425009290777766560",
    "question": "5424993742996153466",
    "shield": "5422562473679037332",
    "wastebasket": "5424629405215401335",
    "white_check_mark": "5422382480189599565",
    "x": "5422848570040558416",
}


def icon(name: str, color: ButtonStyle | None = None, when: WhenCondition = None) -> Style:
    """Button style carrying a pack icon and, for confirm/cancel-type actions
    only, an accent color - plain navigation buttons stay icon-only so color
    reads as a deliberate signal rather than decoration. `icon(a, when=X) |
    icon(b, when=~X)` picks whichever alternative's condition matches."""
    return Style(style=color, emoji_id=CUSTOM_EMOJI[name], when=when)


def accent(color: ButtonStyle) -> Style:
    """Color with no icon - for a button like Cancel, where the label
    already says what it does and a leading icon is redundant."""
    return Style(style=color)
