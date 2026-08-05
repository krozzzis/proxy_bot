from aiogram import Router

from .admin import (
    add_user_dialog,
    admin_menu_dialog,
    admins_dialog,
    broadcast_dialog,
    codes_dialog,
    create_code_dialog,
    link_remnawave_dialog,
    users_dialog,
)
from .user import enter_code_dialog, help_dialog, links_dialog, settings_dialog, user_menu_dialog

router = Router(name="dialogs")
router.include_routers(
    user_menu_dialog,
    enter_code_dialog,
    links_dialog,
    help_dialog,
    settings_dialog,
    admin_menu_dialog,
    create_code_dialog,
    codes_dialog,
    users_dialog,
    admins_dialog,
    broadcast_dialog,
    add_user_dialog,
    link_remnawave_dialog,
)
