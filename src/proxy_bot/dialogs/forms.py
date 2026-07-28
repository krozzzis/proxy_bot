from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.style.base import Style
from aiogram_dialog.widgets.text import Format
from pydantic import TypeAdapter, ValidationError

from .common import icon, not_a_command

AsyncCheck = Callable[[Any, DialogManager], Awaitable[str | None]]
OnFieldDone = Callable[[Any, DialogManager], Awaitable[None]]


@dataclass(frozen=True)
class FormField:
    """One scalar step of a form: a prompt, a Pydantic type to validate the
    submitted text against, and (optionally) an extra async check for
    business rules a type alone can't express (e.g. a uniqueness lookup).

    `type_adapter` must be built by the caller, not derived from a Pydantic
    model's `model_fields[name].annotation` - under Pydantic 2.13 that
    attribute drops `Annotated` metadata like `StringConstraints`, so a
    `TypeAdapter` built from it alone would silently stop enforcing the
    field's actual constraints.

    Multi-value "collect several of these" steps (see
    admin/create_code.py's link-entry window) aren't a single scalar value
    and don't fit this shape - they stay hand-written windows.
    """

    name: str
    type_adapter: TypeAdapter[Any]
    prompt: str
    invalid_label: str
    check: AsyncCheck | None = None
    optional: bool = False
    skip_label: str | None = None
    default: Any = None


def build_field_window(
    field: FormField,
    state: State,
    on_done: OnFieldDone,
    cancel_label: str,
    cancel_style: Style,
) -> Window:
    """A Window that prompts for `field`, validates the reply against
    `field.type_adapter` (then `field.check`, if set), and calls
    `on_done(value, manager)` once a valid value is in hand - via the skip
    button when `field.optional` and the admin taps it, otherwise via typed
    input. `on_done` owns what happens next (switch to another state,
    finalize the form, ...); this function only owns getting one valid
    value out of the admin.
    """

    async def on_input(message: Message, widget: ManagedTextInput, manager: DialogManager, raw: str) -> None:
        value = raw.strip()
        try:
            parsed = field.type_adapter.validate_python(value)
        except ValidationError:
            manager.dialog_data["error"] = field.invalid_label
            return
        if field.check is not None:
            error = await field.check(parsed, manager)
            if error is not None:
                manager.dialog_data["error"] = error
                return
        manager.dialog_data.pop("error", None)
        await on_done(parsed, manager)

    async def on_skip(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
        manager.dialog_data.pop("error", None)
        await on_done(field.default, manager)

    async def getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
        prompt = i18n.get(field.prompt)
        error = dialog_manager.dialog_data.get("error")
        if error:
            prompt = f"{i18n.get(error)}\n\n{prompt}"
        result: dict[str, Any] = {"prompt": prompt, "cancel": i18n.get(cancel_label)}
        if field.optional:
            assert field.skip_label is not None, f"field {field.name!r} is optional but has no skip_label"
            result["skip"] = i18n.get(field.skip_label)
        return result

    widgets = [
        Format("{prompt}"),
        TextInput(id=f"form_{field.name}", on_success=on_input, filter=not_a_command),
    ]
    if field.optional:
        widgets.append(
            Button(Format("{skip}"), id=f"form_{field.name}_skip", on_click=on_skip, style=icon("chevron_right"))
        )
    widgets.append(Cancel(Format("{cancel}"), style=cancel_style))

    return Window(*widgets, state=state, getter=getter)
