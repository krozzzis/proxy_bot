from __future__ import annotations

from pathlib import Path


def resolve_logo_path(
    logo_path: Path | None,
    logo_overrides: dict[str, Path],
    locale: str,
) -> Path | None:
    """Pick which branded-logo file to use for `locale`.

    Priority: an explicit BRANDED_LOGO_PATH_<LOCALE> override, then an
    auto-detected `<stem>_<locale><suffix>` sibling of logo_path (e.g.
    logo.png -> logo_ru.png), then logo_path itself as the universal
    fallback. A configured override or auto-detected sibling that doesn't
    actually exist on disk is skipped rather than treated as an error -
    this whole feature is opt-in and forgiving by design (see config.py).
    """
    if logo_path is None:
        return None

    override = logo_overrides.get(locale)
    if override is not None and override.is_file():
        return override

    localized = logo_path.with_name(f"{logo_path.stem}_{locale}{logo_path.suffix}")
    if localized.is_file():
        return localized

    return logo_path
