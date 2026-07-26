### Общие пользовательские сообщения

start-prompt-code = Введите код доступа, который вам выдали.

menu-title-greeting =
    👋 Здравствуйте, { $name }!

    📋 <b>Меню</b>

    Выберите действие:
menu-title =
    📋 <b>Меню</b>

    Выберите действие:
menu-btn-enter-code = ➕ Ввести код
menu-btn-links = 🔑 Мои ссылки
menu-btn-help = ❓ Помощь
menu-btn-back = ◀ Назад

code-invalid = ❌ Код не найден. Проверьте правильность ввода и попробуйте ещё раз.
code-banned = 🚫 Ваш аккаунт заблокирован администратором. Обратитесь в поддержку.
code-already-added = Этот код уже добавлен к вашему аккаунту. Ссылки можно получить командой /link.
code-accepted = ✅ <b>Код принят!</b> Ваши ссылки:
code-prompt-again = Введите новый код доступа.

link-header = 🔑 <b>Ваши ссылки</b>
link-item =
    <b>{ $description }</b> (код: <code>{ $code }</code>)
    { $links }
link-none = У вас пока нет ни одной ссылки. Отправьте /code, чтобы ввести код доступа.

help-text =
    <b>Доступные команды</b>

    /start — начать работу с ботом
    /help — показать это сообщение
    /link — получить свои ссылки
    /code — ввести ещё один код
help-admin-suffix =

    <b>Команды администратора</b>

    /admin — открыть админ-панель

unknown-command = Неизвестная команда. Отправьте /help, чтобы увидеть список доступных команд.
unknown-message = Не понимаю это сообщение. Чтобы ввести код доступа, отправьте /code.
dialog-unknown-intent = Это меню больше не активно (например, бот перезапускался). Отправьте /start или /help.

broadcast-prefix = 📢 <b>Сообщение от администрации</b>

yes = Да
no = Нет

### Админ-панель

admin-only = Эта команда доступна только администраторам.
admin-menu-title =
    ⚙️ <b>Админ-панель</b>

    Выберите действие:
admin-btn-create-code = ➕ Создать код
admin-btn-codes = 📦 Все коды
admin-btn-users = 👤 Пользователи
admin-btn-admins = 🛡 Администраторы
admin-btn-broadcast = 📢 Рассылка
admin-btn-close = ✖ Закрыть
admin-btn-back = ◀ Назад
admin-btn-cancel = Отмена
admin-btn-confirm = ✅ Подтвердить
admin-btn-done = ✅ Готово
admin-btn-undo = ↩ Отменить последнюю

admin-create-code-prompt-code = Введите новый код (латиница, цифры, "-" или "_", до 32 символов):
admin-create-code-invalid = Недопустимый формат кода. Используйте латиницу, цифры, "-" или "_", не длиннее 32 символов.
admin-create-code-exists = Такой код уже существует. Введите другой.
admin-create-code-prompt-link = Отправьте ссылку. Можно добавить несколько — после каждой это сообщение появится снова.
admin-create-code-links-added = Добавлено ссылок: { $count }
admin-create-code-prompt-description = Введите описание кода (или «-», чтобы пропустить):
admin-create-code-done = ✅ Код «{ $code }» создан.

admin-codes-title = 📦 <b>Коды</b> ({ $count })
admin-codes-empty = Пока нет ни одного кода.
admin-codes-item = { $code } — { $description } ({ $count } 🔗)
admin-code-detail-title =
    📦 Код: <b>{ $code }</b>
    Описание: { $description }
admin-code-no-links = Ссылок пока нет.
admin-code-remove-link-btn = ✖ Удалить ссылку #{ $n }
admin-code-link-removed = Ссылка удалена.
admin-btn-add-link = ➕ Добавить ссылку
admin-btn-edit-description = ✏ Изменить описание
admin-btn-delete-code = 🗑 Удалить код
admin-code-add-link-prompt = Отправьте новую ссылку для этого кода.
admin-code-link-added = ✅ Ссылка добавлена.
admin-code-edit-description-prompt = Отправьте новое описание (или «-», чтобы очистить).
admin-code-description-updated = ✅ Описание обновлено.
admin-code-deleted = Код «{ $code }» и все его ссылки удалены.

admin-users-title = 👤 <b>Пользователи</b> ({ $count })
admin-users-empty = Пока нет ни одного пользователя.
admin-users-item = { $name } (id { $id }) — кодов: { $count }
admin-user-detail-title =
    👤 <b>{ $name }</b>
    ID: <code>{ $id }</code>
    Забанен: { $banned }
admin-user-codes-none = У пользователя нет активированных кодов.
admin-user-revoke-btn = ✖ Отобрать «{ $code }»
admin-user-revoke-done = Код «{ $code }» отобран у пользователя { $id }.
admin-user-ban-btn = 🚫 Забанить пользователя
admin-user-unban-btn = ✅ Разбанить пользователя

admin-admins-title = 🛡 <b>Администраторы</b>
admin-admins-item = { $name } (id { $id })
admin-btn-add-admin = ➕ Добавить администратора
admin-add-admin-prompt = Отправьте числовой Telegram ID нового администратора.
admin-add-admin-invalid = Некорректный ID. Отправьте число — Telegram ID пользователя.
admin-add-admin-already = Этот пользователь уже администратор.
admin-add-admin-done = ✅ Пользователь { $id } назначен администратором.

admin-broadcast-target-prompt = 📢 Кому отправить сообщение?
admin-broadcast-target-all = Всем пользователям
admin-broadcast-target-code = По коду
admin-broadcast-choose-code = Выберите код:
admin-broadcast-no-codes = Пока нет ни одного кода.
admin-broadcast-prompt-text = Введите текст сообщения для рассылки:
admin-broadcast-confirm =
    📢 Отправить сообщение { $count } пользователям?

    { $text }
admin-broadcast-done = ✅ Рассылка завершена: { $sent } доставлено, { $failed } ошибок.
admin-broadcast-empty = Нет получателей для рассылки.
