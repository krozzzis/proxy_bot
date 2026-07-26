from __future__ import annotations

from pathlib import Path

from aiogram_i18n import I18nMiddleware
from aiogram_i18n.cores import FluentCompileCore
from aiogram_i18n.managers.memory import MemoryManager


def build_i18n_middleware(locales_dir: Path, default_locale: str) -> I18nMiddleware:
    core = FluentCompileCore(
        path=locales_dir / "{locale}",
        default_locale=default_locale,
    )
    manager = MemoryManager(default_locale=default_locale)
    return I18nMiddleware(core=core, manager=manager, default_locale=default_locale)
