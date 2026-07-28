### Общие пользовательские сообщения

start-prompt-code = Введите код доступа, который вам выдали.

menu-title-greeting =
    { "" }[tg_emoji:5424978921064013406:wave] Здравствуйте, { $name }!

    { "" }[tg_emoji:5424716580166607793:clipboard] <b>Личный кабинет</b>
    Активных кодов: { $count }

    Выберите действие:
menu-title =
    { "" }[tg_emoji:5424716580166607793:clipboard] <b>Личный кабинет</b>
    Активных кодов: { $count }

    Выберите действие:
menu-btn-enter-code = Ввести код
menu-btn-links = Мои ссылки
menu-btn-help = Помощь
menu-btn-back = Назад
menu-btn-admin = Админ-панель

code-invalid = [tg_emoji:5422848570040558416:x] Код не найден. Проверьте правильность ввода и попробуйте ещё раз.
code-banned = [tg_emoji:5424910789997797782:no_entry_sign] Ваш аккаунт заблокирован администратором. Обратитесь в поддержку.
code-already-added = [tg_emoji:5422382480189599565:white_check_mark] Этот код уже добавлен к вашему аккаунту.
code-accepted = [tg_emoji:5422382480189599565:white_check_mark] <b>Код принят!</b>
code-prompt-again = Введите новый код доступа.

link-header = [tg_emoji:5424947786846085477:key] <b>Ваши ссылки</b>
link-item =
    { "" }[tg_emoji:5424983971945553033:small_blue_diamond] <b>{ $description }</b>
    Код: <code>{ $code }</code>

    { $links }
link-none = У вас пока нет ни одной ссылки. Нажмите «Ввести код», чтобы получить доступ.

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

broadcast-prefix = [tg_emoji:5422785094718894954:loudspeaker] <b>Сообщение от администрации</b>

yes = Да
no = Нет

### Админ-панель

admin-only = Эта команда доступна только администраторам.
admin-menu-title =
    { "" }[tg_emoji:5424814720169322177:gear] <b>Админ-панель</b>

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

admin-create-code-prompt-code = Введите новый код (латиница, цифры, "-" или "_", до 32 символов):
admin-create-code-invalid = Недопустимый формат кода. Используйте латиницу, цифры, "-" или "_", не длиннее 32 символов.
admin-create-code-exists = Такой код уже существует. Введите другой.
admin-create-code-prompt-link = Отправьте ссылку. Можно добавить несколько — после каждой это сообщение появится снова.
admin-create-code-links-added = Добавлено ссылок: { $count }
admin-create-code-prompt-description = Введите описание кода (или «-», чтобы пропустить):
admin-create-code-done = [tg_emoji:5422382480189599565:white_check_mark] Код «{ $code }» создан.

admin-codes-title = [tg_emoji:5425024619516044042:package] <b>Коды</b> ({ $count })
admin-codes-empty = Пока нет ни одного кода.
admin-codes-item = { $code } — { $description } ({ $count } ссылок)
admin-code-detail-title =
    { "" }[tg_emoji:5425024619516044042:package] Код: <b>{ $code }</b>
    Описание: { $description }
admin-code-no-links = Ссылок пока нет.
admin-code-remove-link-btn = Удалить ссылку #{ $n }
admin-code-link-removed = Ссылка удалена.
admin-btn-add-link = Добавить ссылку
admin-btn-edit-description = Изменить описание
admin-btn-delete-code = Удалить код
admin-code-add-link-prompt = Отправьте новую ссылку для этого кода.
admin-code-link-added = [tg_emoji:5422382480189599565:white_check_mark] Ссылка добавлена.
admin-code-edit-description-prompt = Отправьте новое описание (или «-», чтобы очистить).
admin-code-description-updated = [tg_emoji:5422382480189599565:white_check_mark] Описание обновлено.
admin-code-deleted = Код «{ $code }» и все его ссылки удалены.

admin-users-title = [tg_emoji:5422406733869920062:bust_in_silhouette] <b>Пользователи</b> ({ $count })
admin-users-empty = Пока нет ни одного пользователя.
admin-users-item = { $name } (id { $id }) — кодов: { $count }
admin-user-detail-title =
    { "" }[tg_emoji:5422406733869920062:bust_in_silhouette] <b>{ $name }</b>
    ID: <code>{ $id }</code>
    Забанен: { $banned }
admin-user-codes-none = У пользователя нет активированных кодов.
admin-user-revoke-btn = Отобрать «{ $code }»
admin-user-revoke-done = Код «{ $code }» отобран у пользователя { $id }.
admin-user-ban-btn = Забанить пользователя
admin-user-unban-btn = Разбанить пользователя

admin-admins-title = [tg_emoji:5422562473679037332:shield] <b>Администраторы</b>
admin-admins-item = { $name } (id { $id })
admin-btn-add-admin = Добавить администратора
admin-add-admin-prompt = Отправьте числовой Telegram ID нового администратора.
admin-add-admin-invalid = Некорректный ID. Отправьте число — Telegram ID пользователя.
admin-add-admin-already = Этот пользователь уже администратор.
admin-add-admin-done = [tg_emoji:5422382480189599565:white_check_mark] Пользователь { $id } назначен администратором.

admin-broadcast-target-prompt = [tg_emoji:5422785094718894954:loudspeaker] Кому отправить сообщение?
admin-broadcast-target-all = Всем пользователям
admin-broadcast-target-code = По коду
admin-broadcast-choose-code = Выберите код:
admin-broadcast-no-codes = Пока нет ни одного кода.
admin-broadcast-prompt-text = Введите текст сообщения для рассылки:
admin-broadcast-confirm =
    { "" }[tg_emoji:5422785094718894954:loudspeaker] Отправить сообщение { $count } пользователям?

    { $text }
admin-broadcast-done = [tg_emoji:5422382480189599565:white_check_mark] Рассылка завершена: { $sent } доставлено, { $failed } ошибок.
admin-broadcast-empty = Нет получателей для рассылки.
