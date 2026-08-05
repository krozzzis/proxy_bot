from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import DialogManager, Window
from aiogram_dialog.widgets.common import BaseWidget
from aiogram_dialog.widgets.input import ManagedTextInput, MessageInput, TextInput
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Multi
from pydantic import TypeAdapter, ValidationError

from .common import icon, not_a_command
from .widgets import I18N

AsyncCheck = Callable[[Any, DialogManager], Awaitable[str | None]]
OnFieldDone = Callable[[Any, DialogManager], Awaitable[None]]
ExtraGetter = Callable[[DialogManager], Awaitable[dict]]

# Shared default for FormField.optional fields that don't need a wording
# more specific than "leave this blank" (e.g. the broadcast title's own
# "empty title" button uses its own label instead).
DEFAULT_SKIP_LABEL = "form-btn-leave-empty"


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
    rich: bool = False
    """When set, the field captures a Telegram message's HTML-formatted
    text as-is (via `Message.html_text`) instead of a stripped plain
    string - entities like custom emoji round-trip intact. Used for
    values that are themselves rich content (e.g. the broadcast title),
    not scalar data a Pydantic type can validate; `type_adapter` is still
    called on the extracted text so a passthrough `TypeAdapter(str)` is
    the usual choice."""
    extra_getter: ExtraGetter | None = None
    """Extra window-getter data merged in alongside `error`, so `prompt`
    can interpolate live dialog state (e.g. the current value being
    replaced) via Fluent `{ $var }` placeholders."""


def build_field_window(
    field: FormField,
    state: State,
    on_done: OnFieldDone,
    back_widget: BaseWidget,
) -> Window:
    """A Window that prompts for `field`, validates the reply against
    `field.type_adapter` (then `field.check`, if set), and calls
    `on_done(value, manager)` once a valid value is in hand - via the skip
    button when `field.optional` and the admin taps it, otherwise via typed
    input. `on_done` owns what happens next (switch to another state,
    finalize the form, ...); this function only owns getting one valid
    value out of the admin.

    `back_widget` is whatever "leave this step" means for the caller: a
    `Cancel(...)` that ends the whole form, or a `SwitchTo(...)` that
    returns to some earlier step without losing what it already collected.
    """

    # dialog_data is shared by every window in a Dialog, so a bare "error"
    # key would leak between fields that live in the same form (e.g.
    # admin/codes.py has three FormField windows on one Dialog) - an error
    # left over from one field would render on the next one's window too.
    error_key = f"error_{field.name}"

    async def _validate(value: str, manager: DialogManager) -> None:
        try:
            parsed = field.type_adapter.validate_python(value)
        except ValidationError:
            manager.dialog_data[error_key] = field.invalid_label
            return
        if field.check is not None:
            error = await field.check(parsed, manager)
            if error is not None:
                manager.dialog_data[error_key] = error
                return
        manager.dialog_data.pop(error_key, None)
        await on_done(parsed, manager)

    async def on_input(message: Message, widget: ManagedTextInput, manager: DialogManager, raw: str) -> None:
        await _validate(raw.strip(), manager)

    async def on_rich_input(message: Message, widget: MessageInput, manager: DialogManager) -> None:
        await _validate(message.html_text, manager)

    async def on_skip(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
        manager.dialog_data.pop(error_key, None)
        await on_done(field.default, manager)

    async def getter(dialog_manager: DialogManager, **kwargs) -> dict:
        data = {"error": dialog_manager.dialog_data.get(error_key)}
        if field.extra_getter is not None:
            data.update(await field.extra_getter(dialog_manager))
        return data

    widgets = [
        Multi(I18N("{error}", when="error"), I18N(field.prompt), sep="\n\n"),
        MessageInput(on_rich_input, content_types=ContentType.TEXT, filter=not_a_command)
        if field.rich
        else TextInput(id=f"form_{field.name}", on_success=on_input, filter=not_a_command),
    ]
    if field.optional:
        skip_label = field.skip_label or DEFAULT_SKIP_LABEL
        widgets.append(
            Button(I18N(skip_label), id=f"form_{field.name}_skip", on_click=on_skip, style=icon("chevron_right"))
        )
    widgets.append(back_widget)

    return Window(*widgets, state=state, getter=getter)
