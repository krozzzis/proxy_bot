from aiogram.types import Message


def not_a_command(message: Message) -> bool:
    """TextInput filter: reject slash-commands so they fall through to command handlers."""
    return not (message.text or "").startswith("/")


# Custom-emoji document ids from the bot's Material Symbols icon pack
# (scripts/generate_emoji_pack.py), for buttons in the main user/admin
# menus - Telegram inline buttons carry these via a dedicated
# icon_custom_emoji_id field (aiogram_dialog: Style(emoji_id=...)), not via
# text entities, so the button label text itself stays a plain string with
# no :shortcode: prefix. Regenerating the pack rotates every id here.
CUSTOM_EMOJI = {
    "arrow_backward": "5422814592554280129",
    "bust_in_silhouette": "5424676319143174198",
    "gear": "5422765402293839322",
    "heavy_plus_sign": "5425076957987513993",
    "key": "5425059460290748236",
    "loudspeaker": "5425041283989154189",
    "package": "5422753565363971729",
    "question": "5422644765252429636",
    "shield": "5424784870146611833",
}
