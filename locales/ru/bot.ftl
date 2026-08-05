### Общие пользовательские сообщения

start-prompt-code = Введите код доступа, который вам выдали.

menu-title-greeting =
    { $emoji_wave } Здравствуйте, { $name }!

    { $emoji_clipboard } <b>Личный кабинет</b>

    Активных подписок: { $count }

    Выберите действие:
menu-title =
    { $emoji_clipboard } <b>Личный кабинет</b>

    Активных подписок: { $count }

    Выберите действие:
menu-btn-enter-code = Ввести код
menu-btn-links = Мои подписки
menu-btn-help = Помощь
menu-btn-back = Назад
menu-btn-admin = Админ-панель
menu-btn-settings = Настройки

settings-title =
    { $emoji_gear } <b>Настройки</b>

    Выберите действие:
settings-btn-language = Язык
settings-language-title =
    { $emoji_language } <b>Язык</b>

    Выберите язык интерфейса:

code-invalid = { $emoji_x } Код не найден. Проверьте правильность ввода и попробуйте ещё раз.
code-banned = { $emoji_no_entry_sign } Ваш аккаунт заблокирован администратором. Обратитесь в поддержку.
code-already-added = { $emoji_white_check_mark } Этот код уже добавлен к вашему аккаунту.
code-accepted = { $emoji_white_check_mark } <b>Код принят!</b>
code-prompt-again = Введите новый код доступа.

link-header = { $emoji_key } <b>Ваши подписки</b>
link-item =
    { $emoji_small_blue_diamond } <b>{ $description }</b>
    Код: <code>{ $code }</code>

    { $links }
link-help-hint = Команда /help подскажет, как пользоваться подпиской.
link-none = У вас пока нет ни одной подписки. Нажмите «Ввести код», чтобы получить доступ.

help-text =
    <b>Доступные команды</b>

    /start — начать работу с ботом
    /help — показать это сообщение
    /link — получить свои подписки
    /code — ввести ещё один код

help-admin-suffix =
    <b>Команды администратора</b>

    /admin — открыть админ-панель

unknown-command = Неизвестная команда. Отправьте /help, чтобы увидеть список доступных команд.
unknown-message = Не понимаю это сообщение. Чтобы ввести код доступа, отправьте /code.

broadcast-prefix = { $emoji_loudspeaker } <b>Сообщение от администрации</b>

yes = Да
no = Нет

### Админ-панель

admin-only = Эта команда доступна только администраторам.
admin-menu-title =
    { $emoji_gear } <b>Админ-панель</b>

    Выберите действие:
admin-btn-create-code = Создать код
admin-btn-codes = Все коды
admin-btn-users = Пользователи
admin-btn-admins = Администраторы
admin-btn-broadcast = Рассылка
admin-btn-close = Назад
admin-btn-back = Назад
admin-btn-prev = Пред.
admin-btn-next = След.
admin-btn-cancel = Отмена
admin-btn-confirm = Подтвердить
admin-btn-done = Готово
admin-btn-undo = Отменить последнюю
admin-btn-skip = Пропустить

admin-create-code-prompt-code = Введите новый код (латиница, цифры, "-" или "_", от 8 до 32 символов):
admin-create-code-invalid = Недопустимый формат кода. Используйте латиницу, цифры, "-" или "_", от 8 до 32 символов.
admin-create-code-exists = Такой код уже существует. Введите другой.
admin-create-code-prompt-link = Отправьте ссылку. Можно добавить несколько — после каждой это сообщение появится снова.
admin-create-code-links-added = Добавлено ссылок: { $count }
admin-create-code-prompt-description = Введите описание подписки:
admin-create-code-prompt-squads = Выберите сквады Remnawave, которые получит пользователь при активации этого кода (можно пропустить):
admin-create-code-squads-empty = Сквады Remnawave недоступны — код будет создан только с фиксированными ссылками.
admin-create-code-squad-item = { $name }
admin-create-code-done = { $emoji_white_check_mark } Код «{ $code }» создан.

admin-page-indicator = · { $page }/{ $total }
admin-codes-title = { $emoji_package } <b>Коды</b> ({ $count })
admin-codes-empty = Пока нет ни одного кода.
admin-codes-item = { $code } — { $description } ({ $count } ссылок)
admin-code-detail-title =
    { $emoji_package } <b>{ $code }</b>

    Подписка: { $description }
admin-code-no-links = Ссылок пока нет.
admin-code-remove-link-btn = Удалить ссылку #{ $n }
admin-code-link-removed = Ссылка удалена.
admin-btn-add-link = Добавить ссылку
admin-btn-edit-code = Переименовать код
admin-btn-edit-description = Изменить описание
admin-btn-delete-code = Удалить код
admin-code-add-link-prompt = Отправьте новую ссылку для этого кода.
admin-code-link-added = { $emoji_white_check_mark } Ссылка добавлена.
admin-code-edit-name-prompt = Отправьте новое имя для этого кода (латиница, цифры, «-» или «_», от 8 до 32 символов). Все, у кого уже есть этот код, сохранят доступ под новым именем.
admin-code-renamed = { $emoji_white_check_mark } Код «{ $old }» переименован в «{ $new }».
admin-code-edit-description-prompt = Отправьте новое описание (или «-», чтобы очистить).
admin-code-description-updated = { $emoji_white_check_mark } Описание обновлено.
admin-code-deleted = Код «{ $code }» и все его ссылки удалены.
admin-code-squads-count = Remnawave-сквадов: { $count }
admin-btn-edit-squads = Remnawave-сквады
admin-code-edit-squads-prompt = Выберите сквады Remnawave для этого кода:
admin-code-squads-updated = { $emoji_white_check_mark } Сквады обновлены.

admin-users-title = { $emoji_bust_in_silhouette } <b>Пользователи</b> ({ $count })
admin-users-empty = Пока нет ни одного пользователя.
admin-users-item = { $name } (id { $id }) — кодов: { $count }
admin-user-detail-title =
    { $emoji_bust_in_silhouette } <b>{ $name }</b>

    ID: <code>{ $id }</code>
    Забанен: { $banned }
admin-user-codes-none = У пользователя нет активированных кодов.
admin-user-revoke-btn = Отобрать «{ $code }»
admin-user-revoke-done = Код «{ $code }» отобран у пользователя { $id }.
admin-user-ban-btn = Забанить пользователя
admin-user-unban-btn = Разбанить пользователя
admin-user-ban-admin-denied = Нельзя забанить администратора. Сначала снимите права в разделе «Администраторы».
admin-user-remnawave-linked = Remnawave: { $username } ({ $source })
admin-user-remnawave-link-source-auto = автоматически
admin-user-remnawave-link-source-manual = вручную
admin-btn-link-remnawave = Привязать Remnawave
admin-link-remnawave-prompt = Введите Remnawave-username пользователя, которого нужно привязать к id { $id }:
admin-link-remnawave-not-found = Пользователь с таким username не найден в Remnawave.
admin-link-remnawave-lookup-failed = Не удалось обратиться к Remnawave. Попробуйте ещё раз.
admin-link-remnawave-confirm =
    Привязать Remnawave-аккаунт «{ $username }» к пользователю id { $id }?

    { $url }
admin-link-remnawave-done = { $emoji_white_check_mark } Remnawave-аккаунт привязан к пользователю { $id }.

admin-admins-title = { $emoji_shield } <b>Администраторы</b> ({ $count })
admin-admins-item = { $name } (id { $id })
admin-btn-add-admin = Добавить администратора
admin-add-admin-choose-method-prompt = Как указать нового администратора?
admin-add-admin-method-id = По ID
admin-add-admin-method-username = По username
admin-add-admin-prompt = Отправьте числовой Telegram ID нового администратора.
admin-add-admin-invalid = Некорректный ID. Отправьте число — Telegram ID пользователя.
admin-add-admin-prompt-username = Отправьте username пользователя (с @ или без). Пользователь должен хотя бы раз запустить бота.
admin-add-admin-username-invalid = Пользователь с таким username не найден. Возможно, он ещё не запускал бота — используйте числовой ID.
admin-add-admin-already = Этот пользователь уже администратор.
admin-add-admin-done = { $emoji_white_check_mark } Пользователь { $id } назначен администратором.
admin-remove-admin-btn = Снять права — { $name }
admin-remove-admin-done = Права администратора сняты с пользователя { $id }.

admin-btn-add-user = Добавить пользователя
admin-add-user-prompt = Отправьте Telegram ID или username пользователя (с @ или без).
admin-add-user-invalid = Пользователь не найден. Если он ещё не запускал бота, укажите его числовой ID.
admin-add-user-subs-title = Выберите, какие подписки подключить пользователю { $name } (id { $id }):
admin-add-user-subs-empty = Пока нет ни одного кода. Сначала создайте код в разделе «Все коды».
admin-add-user-sub-item = { $code } — { $description }
admin-add-user-done = { $emoji_white_check_mark } Пользователь { $id } добавлен. Подключено подписок: { $count }.

admin-broadcast-target-prompt = { $emoji_loudspeaker } Кому отправить сообщение?
admin-broadcast-target-all = Всем пользователям
admin-broadcast-target-code = По коду
admin-broadcast-choose-code = Выберите код:
admin-broadcast-no-codes = Пока нет ни одного кода.
admin-broadcast-prompt-text = Введите текст сообщения для рассылки:
admin-broadcast-confirm =
    { $emoji_loudspeaker } Отправить сообщение { $count } пользователям?

    { $text }
admin-broadcast-done = { $emoji_white_check_mark } Рассылка завершена: { $sent } доставлено, { $failed } ошибок.
admin-broadcast-empty = Нет получателей для рассылки.
