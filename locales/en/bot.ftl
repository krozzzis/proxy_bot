### Common user-facing messages

start-prompt-code = Enter the access code you were given.

menu-title-greeting =
    :wave: Hello, { $name }!

    :clipboard: <b>Menu</b>

    Choose an action:
menu-title =
    :clipboard: <b>Menu</b>

    Choose an action:
menu-btn-enter-code = :heavy_plus_sign: Enter code
menu-btn-links = :key: My links
menu-btn-help = :question: Help
menu-btn-back = :arrow_backward: Back
menu-btn-admin = :gear: Admin panel

code-invalid = :x: Code not found. Check it and try again.
code-banned = :no_entry_sign: Your account has been banned by an administrator. Please contact support.
code-already-added = :white_check_mark: This code is already linked to your account.
code-accepted = :white_check_mark: <b>Code accepted!</b>
code-prompt-again = Enter another access code.

link-header = :key: <b>Your links</b>
link-item =
    <b>{ $description }</b> (code: <code>{ $code }</code>)
    { $links }
link-none = You don't have any links yet. Send /code to enter an access code.

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

broadcast-prefix = :loudspeaker: <b>Message from the administration</b>

yes = Yes
no = No

### Admin panel

admin-only = This command is available to administrators only.
admin-menu-title =
    :gear: <b>Admin panel</b>

    Choose an action:
admin-btn-create-code = :heavy_plus_sign: Create code
admin-btn-codes = :package: All codes
admin-btn-users = :bust_in_silhouette: Users
admin-btn-admins = :shield: Admins
admin-btn-broadcast = :loudspeaker: Broadcast
admin-btn-close = :arrow_backward: Back
admin-btn-back = :arrow_backward: Back
admin-btn-cancel = :x: Cancel
admin-btn-confirm = :white_check_mark: Confirm
admin-btn-done = :white_check_mark: Done
admin-btn-undo = :leftwards_arrow_with_hook: Undo last

admin-create-code-prompt-code = Enter a new code (letters, digits, "-" or "_", up to 32 characters):
admin-create-code-invalid = Invalid code format. Use letters, digits, "-" or "_", no longer than 32 characters.
admin-create-code-exists = This code already exists. Enter another one.
admin-create-code-prompt-link = Send a link. You can add several — this message reappears after each one.
admin-create-code-links-added = Links added: { $count }
admin-create-code-prompt-description = Enter a description for the code (or "-" to skip):
admin-create-code-done = :white_check_mark: Code "{ $code }" created.

admin-codes-title = :package: <b>Codes</b> ({ $count })
admin-codes-empty = There are no codes yet.
admin-codes-item = { $code } — { $description } ({ $count } :link:)
admin-code-detail-title =
    :package: Code: <b>{ $code }</b>
    Description: { $description }
admin-code-no-links = No links yet.
admin-code-remove-link-btn = :x: Remove link #{ $n }
admin-code-link-removed = Link removed.
admin-btn-add-link = :heavy_plus_sign: Add link
admin-btn-edit-description = :pencil2: Edit description
admin-btn-delete-code = :wastebasket: Delete code
admin-code-add-link-prompt = Send a new link for this code.
admin-code-link-added = :white_check_mark: Link added.
admin-code-edit-description-prompt = Send a new description (or "-" to clear it).
admin-code-description-updated = :white_check_mark: Description updated.
admin-code-deleted = Code "{ $code }" and all its links have been deleted.

admin-users-title = :bust_in_silhouette: <b>Users</b> ({ $count })
admin-users-empty = There are no users yet.
admin-users-item = { $name } (id { $id }) — codes: { $count }
admin-user-detail-title =
    :bust_in_silhouette: <b>{ $name }</b>
    ID: <code>{ $id }</code>
    Banned: { $banned }
admin-user-codes-none = This user has no activated codes.
admin-user-revoke-btn = :x: Revoke "{ $code }"
admin-user-revoke-done = Code "{ $code }" revoked from user { $id }.
admin-user-ban-btn = :no_entry_sign: Ban user
admin-user-unban-btn = :white_check_mark: Unban user

admin-admins-title = :shield: <b>Administrators</b>
admin-admins-item = { $name } (id { $id })
admin-btn-add-admin = :heavy_plus_sign: Add administrator
admin-add-admin-prompt = Send the numeric Telegram ID of the new administrator.
admin-add-admin-invalid = Invalid ID. Send a number — the user's Telegram ID.
admin-add-admin-already = This user is already an administrator.
admin-add-admin-done = :white_check_mark: User { $id } is now an administrator.

admin-broadcast-target-prompt = :loudspeaker: Who should receive the message?
admin-broadcast-target-all = All users
admin-broadcast-target-code = By code
admin-broadcast-choose-code = Choose a code:
admin-broadcast-no-codes = There are no codes yet.
admin-broadcast-prompt-text = Enter the broadcast message text:
admin-broadcast-confirm =
    :loudspeaker: Send this message to { $count } users?

    { $text }
admin-broadcast-done = :white_check_mark: Broadcast finished: { $sent } delivered, { $failed } failed.
admin-broadcast-empty = No recipients for this broadcast.
