### Common user-facing messages

start-prompt-code = Enter the access code you were given.

menu-title-greeting =
    👋 Hello, { $name }!

    📋 <b>Menu</b>

    Choose an action:
menu-title =
    📋 <b>Menu</b>

    Choose an action:
menu-btn-enter-code = ➕ Enter code
menu-btn-links = 🔑 My links
menu-btn-help = ❓ Help
menu-btn-back = ◀ Back

code-invalid = ❌ Code not found. Check it and try again.
code-banned = 🚫 Your account has been banned by an administrator. Please contact support.
code-already-added = This code is already linked to your account. Get the links with /link.
code-accepted = ✅ <b>Code accepted!</b> Here are your links:
code-prompt-again = Enter another access code.

link-header = 🔑 <b>Your links</b>
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
dialog-unknown-intent = This menu is no longer active (the bot may have restarted). Send /start or /help.

broadcast-prefix = 📢 <b>Message from the administration</b>

yes = Yes
no = No

### Admin panel

admin-only = This command is available to administrators only.
admin-menu-title =
    ⚙️ <b>Admin panel</b>

    Choose an action:
admin-btn-create-code = ➕ Create code
admin-btn-codes = 📦 All codes
admin-btn-users = 👤 Users
admin-btn-admins = 🛡 Admins
admin-btn-broadcast = 📢 Broadcast
admin-btn-close = ✖ Close
admin-btn-back = ◀ Back
admin-btn-cancel = Cancel
admin-btn-confirm = ✅ Confirm
admin-btn-done = ✅ Done
admin-btn-undo = ↩ Undo last

admin-create-code-prompt-code = Enter a new code (letters, digits, "-" or "_", up to 32 characters):
admin-create-code-invalid = Invalid code format. Use letters, digits, "-" or "_", no longer than 32 characters.
admin-create-code-exists = This code already exists. Enter another one.
admin-create-code-prompt-link = Send a link. You can add several — this message reappears after each one.
admin-create-code-links-added = Links added: { $count }
admin-create-code-prompt-description = Enter a description for the code (or "-" to skip):
admin-create-code-done = ✅ Code "{ $code }" created.

admin-codes-title = 📦 <b>Codes</b> ({ $count })
admin-codes-empty = There are no codes yet.
admin-codes-item = { $code } — { $description } ({ $count } 🔗)
admin-code-detail-title =
    📦 Code: <b>{ $code }</b>
    Description: { $description }
admin-code-no-links = No links yet.
admin-code-remove-link-btn = ✖ Remove link #{ $n }
admin-code-link-removed = Link removed.
admin-btn-add-link = ➕ Add link
admin-btn-edit-description = ✏ Edit description
admin-btn-delete-code = 🗑 Delete code
admin-code-add-link-prompt = Send a new link for this code.
admin-code-link-added = ✅ Link added.
admin-code-edit-description-prompt = Send a new description (or "-" to clear it).
admin-code-description-updated = ✅ Description updated.
admin-code-deleted = Code "{ $code }" and all its links have been deleted.

admin-users-title = 👤 <b>Users</b> ({ $count })
admin-users-empty = There are no users yet.
admin-users-item = { $name } (id { $id }) — codes: { $count }
admin-user-detail-title =
    👤 <b>{ $name }</b>
    ID: <code>{ $id }</code>
    Banned: { $banned }
admin-user-codes-none = This user has no activated codes.
admin-user-revoke-btn = ✖ Revoke "{ $code }"
admin-user-revoke-done = Code "{ $code }" revoked from user { $id }.
admin-user-ban-btn = 🚫 Ban user
admin-user-unban-btn = ✅ Unban user

admin-admins-title = 🛡 <b>Administrators</b>
admin-admins-item = { $name } (id { $id })
admin-btn-add-admin = ➕ Add administrator
admin-add-admin-prompt = Send the numeric Telegram ID of the new administrator.
admin-add-admin-invalid = Invalid ID. Send a number — the user's Telegram ID.
admin-add-admin-already = This user is already an administrator.
admin-add-admin-done = ✅ User { $id } is now an administrator.

admin-broadcast-target-prompt = 📢 Who should receive the message?
admin-broadcast-target-all = All users
admin-broadcast-target-code = By code
admin-broadcast-choose-code = Choose a code:
admin-broadcast-no-codes = There are no codes yet.
admin-broadcast-prompt-text = Enter the broadcast message text:
admin-broadcast-confirm =
    📢 Send this message to { $count } users?

    { $text }
admin-broadcast-done = ✅ Broadcast finished: { $sent } delivered, { $failed } failed.
admin-broadcast-empty = No recipients for this broadcast.
