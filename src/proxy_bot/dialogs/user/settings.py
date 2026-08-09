from __future__ import annotations

import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Radio, SwitchTo
from aiogram_dialog.widgets.text import Format

from proxy_bot.utils.audit import actor
from proxy_bot.utils.branding import update_before_mode_logo

from ..common import BRANDED_LOGO_MEDIA, branded_logo_getter, icon
from ..widgets import I18N

logger = logging.getLogger(__name__)

# code -> endonym. Shown as-is, not run through Fluent - a Russian-locale
# user hunting for English needs to see "English", not its Russian
# translation, so there's nothing here for locales/*/bot.ftl to hold.
LANGUAGES = {
    "ru": "Русский",
    "en": "English",
}

_LANGUAGE_RADIO_ID = "language_radio"


class Settings(StatesGroup):
    main = State()
    language = State()


async def open_language(_callback, _button: Button, manager: DialogManager) -> None:
    i18n = manager.middleware_data["i18n"]
    await manager.switch_to(Settings.language)
    radio = manager.find(_LANGUAGE_RADIO_ID)
    if radio is not None:
        # Seeds the widget's own state directly - unlike a real click, this
        # doesn't run through Select's on_click machinery, so it can't
        # trigger on_language_selected below and log/no-op a "switch" that
        # never happened.
        await radio.set_checked(i18n.locale)


async def on_language_selected(_callback, _radio, manager: DialogManager, item_id: str) -> None:
    i18n = manager.middleware_data["i18n"]
    if item_id == i18n.locale:
        return
    user = manager.middleware_data["event_from_user"]
    await i18n.set_locale(item_id)
    logger.info("%s switched language to %s", actor(user), item_id)

    # "caption" mode's logo re-resolves and swaps on its own - it's part of
    # this very window's next render, driven by branded_logo_getter reading
    # the locale we just set. "before" mode's logo is a separate, plain
    # message sent once at /start, entirely outside the dialog framework -
    # nothing else would ever touch it again, so it's updated explicitly
    # here. A no-op if that mode was never used in this chat this process's
    # lifetime (see utils/branding.py).
    bot = manager.middleware_data["bot"]
    logo_path = manager.middleware_data.get("logo_path")
    logo_overrides = manager.middleware_data.get("logo_path_overrides") or {}
    await update_before_mode_logo(bot, user.id, logo_path, logo_overrides, item_id)


async def language_getter(**kwargs) -> dict:
    return {"languages": [{"code": code, "name": name} for code, name in LANGUAGES.items()]}


settings_dialog = Dialog(
    Window(
        BRANDED_LOGO_MEDIA,
        I18N("settings-title"),
        Button(I18N("settings-btn-language"), id="open_language", on_click=open_language, style=icon("language")),
        Cancel(I18N("menu-btn-back"), style=icon("arrow_backward")),
        state=Settings.main,
        getter=branded_logo_getter,
    ),
    Window(
        BRANDED_LOGO_MEDIA,
        I18N("settings-language-title"),
        Radio(
            Format("{item[name]}"),
            Format("{item[name]}"),
            id=_LANGUAGE_RADIO_ID,
            item_id_getter=lambda item: item["code"],
            items="languages",
            on_click=on_language_selected,
            checked_style=icon("check"),
        ),
        SwitchTo(I18N("menu-btn-back"), id="back_to_settings", state=Settings.main, style=icon("arrow_backward")),
        state=Settings.language,
        getter=[language_getter, branded_logo_getter],
    ),
)
