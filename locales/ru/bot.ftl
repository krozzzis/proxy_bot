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
code-locked = { $emoji_shield } Слишком много неверных попыток подряд. Попробуйте ввести код позже.
code-already-added = { $emoji_white_check_mark } Этот код уже добавлен к вашему аккаунту.
code-accepted = { $emoji_white_check_mark } <b>Код принят!</b>
code-prompt-again = Введите новый код доступа.

rate-limited = { $emoji_shield } Слишком быстро — подождите немного.

link-header = { $emoji_key } <b>Ваши подписки</b>
link-choose-prompt = Выберите подписку:
link-detail-header =
    { $emoji_rocket } <b>{ $code }</b>

    { $emoji_format_quote } { $description } { $emoji_format_quote }
link-help-hint = Команда /help подскажет, как пользоваться подпиской.
link-none = У вас пока нет ни одной подписки. Нажмите «Ввести код», чтобы получить доступ.
link-banned-notice = { $emoji_no_entry_sign } <b>Ваша подписка заблокирована администратором.</b>
link-btn-unsubscribe = Отказаться от подписки
link-unsubscribe-confirm =
    { $emoji_no_entry_sign } <b>Отказаться от подписки «{ $code }»?</b>

    { $description }

    Доступ будет отключён немедленно. Чтобы пользоваться подпиской снова, потребуется ввести код заново.
link-btn-unsubscribe-confirm = Да, отказаться
link-btn-unsubscribe-cancel = Нет, оставить
link-unsubscribed-done = { $emoji_white_check_mark } Вы отказались от подписки. Доступ отключён.

sub-expiry-normal = Срок действия: до { $date }
sub-expiry-eternal = Срок действия: неограниченно { $emoji_infinity }
sub-traffic-normal = { $used } / { $limit } ГБ
sub-traffic-unlimited = { $used } ГБ / { $emoji_infinity }

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
admin-btn-squads = Сквады
admin-btn-close = Назад
admin-btn-back = Назад
admin-btn-prev = Пред.
admin-btn-next = След.
admin-btn-cancel = Отмена
admin-btn-confirm = Подтвердить
admin-btn-done = Готово
admin-btn-undo = Отменить последнюю
admin-btn-skip = Пропустить
form-btn-leave-empty = Оставить пустым

admin-create-code-prompt-code = Введите новый код (латиница, цифры, "-" или "_", от 8 до 32 символов):
admin-create-code-invalid = Недопустимый формат кода. Используйте латиницу, цифры, "-" или "_", от 8 до 32 символов.
admin-create-code-exists = Такой код уже существует. Введите другой.
admin-create-code-prompt-link = Отправьте ссылку. Можно добавить несколько — после каждой это сообщение появится снова.
admin-create-code-links-added = Добавлено ссылок: { $count }
admin-create-code-link-name-prompt = Введите название для этой ссылки (необязательно):
admin-create-code-prompt-description = Введите описание подписки:
admin-create-code-choose-squad-prompt = Выберите Сквад для этой Remnawave-ссылки:
admin-create-code-squads-empty = Нет доступных Сквадов — создайте Сквад в разделе «Сквады» админ-панели или сначала используйте все существующие.
admin-create-code-squad-item = { $name }
admin-create-code-done = { $emoji_white_check_mark } Код «{ $code }» создан.

admin-page-indicator = · { $page }/{ $total }
admin-codes-title = { $emoji_package } <b>Коды</b> ({ $count })
admin-codes-empty = Пока нет ни одного кода.
admin-codes-item = { $code }
admin-code-detail-title =
    { $emoji_package } <b>{ $code }</b>

    Подписка: { $description }
admin-code-links-count = Ссылок: { $count }
admin-btn-manage-links = Ссылки
admin-code-links-title = { $emoji_link } <b>Ссылки — { $code }</b>
admin-code-no-links = Ссылок пока нет.
admin-code-link-removed = Ссылка удалена.
admin-code-link-row = { $type } — { $value }
admin-code-link-row-named = { $name } ({ $type }) — { $value }
admin-code-link-row-disabled = { $emoji_no_entry_sign } { $row } (отключена)
admin-code-link-type-fix = fix
admin-code-link-type-remnawave = remnawave
admin-code-link-squad-missing = Сквад не выбран или был удалён
admin-btn-add-link = Добавить ссылку
admin-btn-add-remnawave-link = Добавить Remnawave-ссылку
admin-code-add-link-type-prompt = Выберите тип ссылки для добавления:
admin-btn-link-type-fix = Фиксированная ссылка
admin-btn-link-type-remnawave = Remnawave-ссылка
admin-code-link-detail-title = { $emoji_link } <b>Ссылка #{ $n } — { $code }</b>
admin-btn-replace-link = Заменить ссылку
admin-code-replace-link-prompt = Отправьте новую ссылку вместо текущей.
admin-code-link-replaced = { $emoji_white_check_mark } Ссылка обновлена.
admin-btn-rename-link = Переименовать
admin-code-link-renamed = { $emoji_white_check_mark } Ссылка переименована.
admin-btn-move-up = ↑ Выше
admin-btn-move-down = ↓ Ниже
admin-btn-disable-link = Отключить ссылку
admin-btn-enable-link = Включить ссылку
admin-code-link-disabled-done = Ссылка отключена. Она больше не видна пользователям.
admin-code-link-enabled-done = Ссылка снова включена.
admin-btn-delete-link = Удалить ссылку
admin-btn-edit-code = Переименовать код
admin-btn-edit-description = Изменить описание
admin-btn-delete-code = Удалить код
admin-code-add-link-prompt = Отправьте новую фиксированную ссылку для этого кода.
admin-code-link-added = { $emoji_white_check_mark } Ссылка добавлена.
admin-code-link-name-prompt = Отправьте название для этой ссылки (необязательно):
admin-code-edit-name-prompt = Отправьте новое имя для этого кода (латиница, цифры, «-» или «_», от 8 до 32 символов). Все, у кого уже есть этот код, сохранят доступ под новым именем.
admin-code-renamed = { $emoji_white_check_mark } Код «{ $old }» переименован в «{ $new }».
admin-code-edit-description-prompt = Отправьте новое описание.
admin-code-description-updated = { $emoji_white_check_mark } Описание обновлено.
admin-code-deleted = Код «{ $code }» и все его ссылки удалены.
admin-btn-disable-remnawave = Отключить Remnawave
admin-btn-enable-remnawave = Включить Remnawave
admin-code-remnawave-disabled-done = { $emoji_no_entry_sign } Remnawave отключён для кода «{ $code }».
admin-code-remnawave-enabled-done = { $emoji_white_check_mark } Remnawave включён для кода «{ $code }».

admin-squads-title = { $emoji_shield } <b>Сквады</b> ({ $count })
admin-squads-empty = Пока нет ни одного Сквада.
admin-squads-item = { $name } [{ $server }]
admin-btn-create-squad = Создать Сквад
admin-squad-create-choose-server-prompt = Выберите сервер Remnawave для нового Сквада:
admin-squad-server-item = { $server }
admin-squad-create-prompt-name = Введите название Сквада (сервер: { $server }):
admin-squad-name-invalid = Название не может быть пустым.
admin-squad-create-prompt-internal-squads = Выберите internal squads Remnawave, которые войдут в этот Сквад:
admin-squad-internal-squads-empty = На этом сервере Remnawave не найдено internal squads.
admin-squad-internal-squad-item = { $name }
admin-squad-created-done = { $emoji_white_check_mark } Сквад «{ $name }» создан.
admin-squad-detail-title = { $emoji_shield } <b>{ $name }</b>
admin-squad-detail-server = Сервер: { $server }
admin-squad-detail-count = Internal squads: { $count }
admin-btn-edit-squad-name = Переименовать
admin-btn-edit-squad-internal-squads = Изменить internal squads
admin-btn-delete-squad = Удалить Сквад
admin-squad-edit-name-prompt = Отправьте новое название Сквада (сервер: { $server }):
admin-squad-renamed = { $emoji_white_check_mark } Сквад переименован.
admin-squad-edit-internal-squads-prompt = Выберите internal squads Remnawave для этого Сквада:
admin-squad-internal-squads-updated = { $emoji_white_check_mark } Internal squads обновлены.
admin-squad-deleted-done = { $emoji_white_check_mark } Сквад удалён. Ссылки, которые на него ссылались, перестанут выдавать доступ — уберите их из соответствующих кодов.

admin-users-title = { $emoji_bust_in_silhouette } <b>Пользователи</b> ({ $count })
admin-users-empty = Пока нет ни одного пользователя.
admin-users-item = { $name } (id { $id }) — кодов: { $count }
admin-user-detail-title =
    { $emoji_bust_in_silhouette } <b>{ $name }</b>

    ID: <code>{ $id }</code>
    Заблокирован: { $banned }
admin-user-codes-none = У пользователя нет активированных кодов.
admin-btn-subscriptions = Подписки ({ $count })
admin-user-subscriptions-title = { $emoji_key } <b>Подписки пользователя { $id }</b>
admin-user-revoke-btn = Отобрать «{ $code }»
admin-user-revoke-done = Код «{ $code }» отобран у пользователя { $id }.
admin-user-ban-btn = Заблокировать пользователя
admin-user-unban-btn = Разблокировать пользователя
admin-user-ban-admin-denied = Нельзя заблокировать администратора. Сначала снимите права в разделе «Администраторы».
admin-user-remnawave-linked = Remnawave [{ $server }]: { $username } ({ $source })
admin-user-remnawave-link-source-auto = авто
admin-user-remnawave-link-source-manual = вручную
admin-btn-link-remnawave = Привязать Remnawave
admin-btn-link-remnawave-server = Привязать: { $server }
admin-btn-unlink-remnawave-server = Отвязать: { $server }
admin-user-remnawave-unlinked-done = { $emoji_white_check_mark } Remnawave-аккаунт отвязан от пользователя { $id }.
admin-user-remnawave-disabled-done = { $emoji_no_entry_sign } Remnawave отключён для пользователя { $id }.
admin-user-remnawave-enabled-done = { $emoji_white_check_mark } Remnawave включён для пользователя { $id }.
admin-link-remnawave-choose-server-prompt = Выберите сервер Remnawave:
admin-link-remnawave-prompt = Введите Remnawave-username пользователя, которого нужно привязать к id { $id } (сервер { $server }):
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
admin-broadcast-prompt-content = Отправьте текст, фото, видео, документ, аудио, голосовое, кружок или стикер для рассылки. Поддерживается форматирование и кастомные эмодзи.
admin-broadcast-edit-title-btn = Изменить заголовок
admin-broadcast-title-prompt =
    Текущий заголовок:
    <code>{ $current_title }</code>

    Отправьте новый заголовок (поддерживается форматирование), или выберите действие ниже.
admin-broadcast-title-empty-btn = Пустой заголовок
admin-broadcast-confirm =
    { $emoji_loudspeaker } Отправить сообщение { $count } пользователям?

    { $preview }
admin-broadcast-done = { $emoji_white_check_mark } Рассылка завершена: { $sent } доставлено.{ $failures }
admin-broadcast-empty = Нет получателей для рассылки.

admin-broadcast-fail-never-started = { $count } пользователям сообщение не доставлено, так как они ещё ни разу не запустили бота.
admin-broadcast-fail-blocked = { $count } пользователям сообщение не доставлено, так как они заблокировали бота.
admin-broadcast-fail-deactivated = { $count } пользователям сообщение не доставлено, так как их аккаунты удалены или деактивированы.
admin-broadcast-fail-other = { $count } пользователям сообщение не доставлено по другой причине.

admin-broadcast-type-photo = Фото
admin-broadcast-type-video = Видео
admin-broadcast-type-animation = GIF-анимация
admin-broadcast-type-document = Документ
admin-broadcast-type-audio = Аудио
admin-broadcast-type-voice = Голосовое сообщение
admin-broadcast-type-video-note = Видео-сообщение
admin-broadcast-type-sticker = Стикер
admin-broadcast-type-other = Содержимое

### Webhook

admin-webhook-fallback-notice =
    ⚠️ Webhook перестал доставлять обновления, бот автоматически переключился на long polling.

    Последняя ошибка Telegram: { $error }
