from __future__ import annotations

from aiogram.types import User


def actor(user: User) -> str:
    """Format a Telegram user for audit log lines: "id=123 (@username)" or
    just "id=123" if the user has no username set."""
    if user.username:
        return f"id={user.id} (@{user.username})"
    return f"id={user.id}"


def actor_id(user_id: int, username: str | None) -> str:
    """Same as actor(), for call sites that only have a bare id + optional
    username on hand (e.g. a target user looked up from storage) rather than
    a full aiogram User object."""
    if username:
        return f"id={user_id} (@{username})"
    return f"id={user_id}"
