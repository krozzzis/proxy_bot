from collections.abc import Sequence

from aiogram_dialog import Dialog

from .admin import admin_menu_dialog, admins_dialog, broadcast_dialog, codes_dialog, create_code_dialog, users_dialog
from .menu import user_menu_dialog


def get_dialogs() -> Sequence[Dialog]:
    return (
        user_menu_dialog(),
        admin_menu_dialog(),
        create_code_dialog(),
        codes_dialog(),
        users_dialog(),
        admins_dialog(),
        broadcast_dialog(),
    )
