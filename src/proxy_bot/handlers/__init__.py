from collections.abc import Sequence

from aiogram import Router

from . import fallback, user
from .errors import on_unknown_dialog_event

__all__ = ["get_command_routers", "get_fallback_routers", "on_unknown_dialog_event"]


def get_command_routers() -> Sequence[Router]:
    """Routers that must be included before dialogs, so commands work in any state."""
    return (user.router,)


def get_fallback_routers() -> Sequence[Router]:
    """Routers that must be included after dialogs, to catch anything unhandled."""
    return (fallback.router,)
