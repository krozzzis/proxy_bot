### Common user-facing messages

start-prompt-code = Enter the access code you were given.

menu-title-greeting =
    { "" }[tg_emoji:5422610611672490482:wave] Hello, { $name }!

    { "" }[tg_emoji:5425029979635229746:clipboard] <b>Personal cabinet</b>
    Active codes: { $count }

    Choose an action:
menu-title =
    { "" }[tg_emoji:5425029979635229746:clipboard] <b>Personal cabinet</b>
    Active codes: { $count }

    Choose an action:
menu-btn-enter-code = Enter code
menu-btn-links = My links
menu-btn-help = Help
menu-btn-back = Back
menu-btn-admin = Admin panel

code-invalid = [tg_emoji:5422801295335533381:x] Code not found. Check it and try again.
code-banned = [tg_emoji:5424811928440577113:no_entry_sign] Your account has been banned by an administrator. Please contact support.
code-already-added = [tg_emoji:5425143379656744388:white_check_mark] This code is already linked to your account.
code-accepted = [tg_emoji:5425143379656744388:white_check_mark] <b>Code accepted!</b>
code-prompt-again = Enter another access code.

link-header = [tg_emoji:5422546651019517877:key] <b>Your links</b>
link-item =
    { "" }[tg_emoji:5424853319040412766:small_blue_diamond] <b>{ $description }</b>
    Code: <code>{ $code }</code>

    { $links }
link-none = You don't have any links yet. Tap "Enter code" to get access.

help-text =
    <b>Available commands</b>

    /start — start using the bot
    /help — show this message
    /link — get your links
    /code — enter another code

help-admin-suffix =
    <b>Admin commands</b>

    /admin — open the admin panel

unknown-command = Unknown command. Send /help to see the list of available commands.
unknown-message = I don't understand this message. Send /code to enter an access code.

broadcast-prefix = [tg_emoji:5422893770276381417:loudspeaker] <b>Message from the administration</b>

yes = Yes
no = No

### Admin panel

admin-only = This command is available to administrators only.
admin-menu-title =
    { "" }[tg_emoji:5422836015851151216:gear] <b>Admin panel</b>

    Choose an action:
admin-btn-create-code = Create code
admin-btn-codes = All codes
admin-btn-users = Users
admin-btn-admins = Admins
admin-btn-broadcast = Broadcast
admin-btn-close = Back
admin-btn-back = Back
admin-btn-prev = Prev
admin-btn-next = Next
admin-btn-cancel = Cancel
admin-btn-confirm = Confirm
admin-btn-done = Done
admin-btn-undo = Undo last
admin-btn-skip = Skip

admin-create-code-prompt-code = Enter a new code (letters, digits, "-" or "_", 8 to 32 characters):
admin-create-code-invalid = Invalid code format. Use letters, digits, "-" or "_", 8 to 32 characters long.
admin-create-code-exists = This code already exists. Enter another one.
admin-create-code-prompt-link = Send a link. You can add several — this message reappears after each one.
admin-create-code-links-added = Links added: { $count }
admin-create-code-prompt-description = Enter a description for the code:
admin-create-code-done = [tg_emoji:5425143379656744388:white_check_mark] Code "{ $code }" created.

admin-page-indicator = · { $page }/{ $total }
admin-codes-title = [tg_emoji:5422519678624899490:package] <b>Codes</b> ({ $count })
admin-codes-empty = There are no codes yet.
admin-codes-item = { $code } — { $description } ({ $count } links)
admin-code-detail-title =
    { "" }[tg_emoji:5422519678624899490:package] Code: <b>{ $code }</b>
    Description: { $description }
admin-code-no-links = No links yet.
admin-code-remove-link-btn = Remove link #{ $n }
admin-code-link-removed = Link removed.
admin-btn-add-link = Add link
admin-btn-edit-description = Edit description
admin-btn-delete-code = Delete code
admin-code-add-link-prompt = Send a new link for this code.
admin-code-link-added = [tg_emoji:5425143379656744388:white_check_mark] Link added.
admin-code-edit-description-prompt = Send a new description (or "-" to clear it).
admin-code-description-updated = [tg_emoji:5425143379656744388:white_check_mark] Description updated.
admin-code-deleted = Code "{ $code }" and all its links have been deleted.

admin-users-title = [tg_emoji:5424728356966933997:bust_in_silhouette] <b>Users</b> ({ $count })
admin-users-empty = There are no users yet.
admin-users-item = { $name } (id { $id }) — codes: { $count }
admin-user-detail-title =
    { "" }[tg_emoji:5424728356966933997:bust_in_silhouette] <b>{ $name }</b>
    ID: <code>{ $id }</code>
    Banned: { $banned }
admin-user-codes-none = This user has no activated codes.
admin-user-revoke-btn = Revoke "{ $code }"
admin-user-revoke-done = Code "{ $code }" revoked from user { $id }.
admin-user-ban-btn = Ban user
admin-user-unban-btn = Unban user

admin-admins-title = [tg_emoji:5422465824029978096:shield] <b>Administrators</b> ({ $count })
admin-admins-item = { $name } (id { $id })
admin-btn-add-admin = Add administrator
admin-add-admin-prompt = Send the numeric Telegram ID of the new administrator.
admin-add-admin-invalid = Invalid ID. Send a number — the user's Telegram ID.
admin-add-admin-already = This user is already an administrator.
admin-add-admin-done = [tg_emoji:5425143379656744388:white_check_mark] User { $id } is now an administrator.

admin-broadcast-target-prompt = [tg_emoji:5422893770276381417:loudspeaker] Who should receive the message?
admin-broadcast-target-all = All users
admin-broadcast-target-code = By code
admin-broadcast-choose-code = Choose a code:
admin-broadcast-no-codes = There are no codes yet.
admin-broadcast-prompt-text = Enter the broadcast message text:
admin-broadcast-confirm =
    { "" }[tg_emoji:5422893770276381417:loudspeaker] Send this message to { $count } users?

    { $text }
admin-broadcast-done = [tg_emoji:5425143379656744388:white_check_mark] Broadcast finished: { $sent } delivered, { $failed } failed.
admin-broadcast-empty = No recipients for this broadcast.
