### Общие пользовательские сообщения

start-prompt-code = Введите код доступа, который вам выдали.

menu-title-greeting =
    :wave: Здравствуйте, { $name }!

    :clipboard: <b>Меню</b>

    Выберите действие:
menu-title =
    :clipboard: <b>Меню</b>

    Выберите действие:
menu-btn-enter-code = :heavy_plus_sign: Ввести код
menu-btn-links =  :key: Мои ссылки
menu-btn-help = :question: Помощь
menu-btn-back = :arrow_backward: Назад

code-invalid = :x: Код не найден. Проверьте правильность ввода и попробуйте ещё раз.
code-banned = :no_entry_sign: Ваш аккаунт заблокирован администратором. Обратитесь в поддержку.
code-already-added = Этот код уже добавлен к вашему аккаунту. Ссылки можно получить командой /link.
code-accepted = :white_check_mark: <b>Код принят!</b> Ваши ссылки:
code-prompt-again = Введите новый код доступа.

link-header = :key: <b>Ваши ссылки</b>
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

broadcast-prefix = :loudspeaker: <b>Сообщение от администрации</b>

yes = Да
no = Нет

### Админ-панель

admin-only = Эта команда доступна только администраторам.
admin-menu-title =
    :gear: <b>Админ-панель</b>

    Выберите действие:
admin-btn-create-code = :heavy_plus_sign: Создать код
admin-btn-codes = :package: Все коды
admin-btn-users = :bust_in_silhouette: Пользователи
admin-btn-admins = :shield: Администраторы
admin-btn-broadcast = :loudspeaker: Рассылка
admin-btn-close = :heavy_multiplication_x: Закрыть
admin-btn-back = :arrow_backward: Назад
admin-btn-cancel = Отмена
admin-btn-confirm = :white_check_mark: Подтвердить
admin-btn-done = :white_check_mark: Готово
admin-btn-undo = :leftwards_arrow_with_hook: Отменить последнюю

admin-create-code-prompt-code = Введите новый код (латиница, цифры, "-" или "_", до 32 символов):
admin-create-code-invalid = Недопустимый формат кода. Используйте латиницу, цифры, "-" или "_", не длиннее 32 символов.
admin-create-code-exists = Такой код уже существует. Введите другой.
admin-create-code-prompt-link = Отправьте ссылку. Можно добавить несколько — после каждой это сообщение появится снова.
admin-create-code-links-added = Добавлено ссылок: { $count }
admin-create-code-prompt-description = Введите описание кода (или «-», чтобы пропустить):
admin-create-code-done = :white_check_mark: Код «{ $code }» создан.

admin-codes-title = :package: <b>Коды</b> ({ $count })
admin-codes-empty = Пока нет ни одного кода.
admin-codes-item = { $code } — { $description } ({ $count } :link:)
admin-code-detail-title =
    :package: Код: <b>{ $code }</b>
    Описание: { $description }
admin-code-no-links = Ссылок пока нет.
admin-code-remove-link-btn = :heavy_multiplication_x: Удалить ссылку #{ $n }
admin-code-link-removed = Ссылка удалена.
admin-btn-add-link = :heavy_plus_sign: Добавить ссылку
admin-btn-edit-description = :pencil2: Изменить описание
admin-btn-delete-code = :wastebasket: Удалить код
admin-code-add-link-prompt = Отправьте новую ссылку для этого кода.
admin-code-link-added = :white_check_mark: Ссылка добавлена.
admin-code-edit-description-prompt = Отправьте новое описание (или «-», чтобы очистить).
admin-code-description-updated = :white_check_mark: Описание обновлено.
admin-code-deleted = Код «{ $code }» и все его ссылки удалены.

admin-users-title = :bust_in_silhouette: <b>Пользователи</b> ({ $count })
admin-users-empty = Пока нет ни одного пользователя.
admin-users-item = { $name } (id { $id }) — кодов: { $count }
admin-user-detail-title =
    :bust_in_silhouette: <b>{ $name }</b>
    ID: <code>{ $id }</code>
    Забанен: { $banned }
admin-user-codes-none = У пользователя нет активированных кодов.
admin-user-revoke-btn = :heavy_multiplication_x: Отобрать «{ $code }»
admin-user-revoke-done = Код «{ $code }» отобран у пользователя { $id }.
admin-user-ban-btn = :no_entry_sign: Забанить пользователя
admin-user-unban-btn = :white_check_mark: Разбанить пользователя

admin-admins-title = :shield: <b>Администраторы</b>
admin-admins-item = { $name } (id { $id })
admin-btn-add-admin = :heavy_plus_sign: Добавить администратора
admin-add-admin-prompt = Отправьте числовой Telegram ID нового администратора.
admin-add-admin-invalid = Некорректный ID. Отправьте число — Telegram ID пользователя.
admin-add-admin-already = Этот пользователь уже администратор.
admin-add-admin-done = :white_check_mark: Пользователь { $id } назначен администратором.

admin-broadcast-target-prompt = :loudspeaker: Кому отправить сообщение?
admin-broadcast-target-all = Всем пользователям
admin-broadcast-target-code = По коду
admin-broadcast-choose-code = Выберите код:
admin-broadcast-no-codes = Пока нет ни одного кода.
admin-broadcast-prompt-text = Введите текст сообщения для рассылки:
admin-broadcast-confirm =
    :loudspeaker: Отправить сообщение { $count } пользователям?

    { $text }
admin-broadcast-done = :white_check_mark: Рассылка завершена: { $sent } доставлено, { $failed } ошибок.
admin-broadcast-empty = Нет получателей для рассылки.
