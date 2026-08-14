### Common user-facing messages

start-prompt-code = Enter the access code you were given.

menu-title-greeting =
    { $emoji_wave } Hello, { $name }!

    { $emoji_clipboard } <b>Personal cabinet</b>

    Active subscriptions: { $count }

    Choose an action:
menu-title =
    { $emoji_clipboard } <b>Personal cabinet</b>

    Active subscriptions: { $count }

    Choose an action:
menu-btn-enter-code = Enter code
menu-btn-links = My subscriptions
menu-btn-help = Help
menu-btn-back = Back
menu-btn-admin = Admin panel
menu-btn-settings = Settings

settings-title =
    { $emoji_gear } <b>Settings</b>

    Choose an action:
settings-btn-language = Language
settings-language-title =
    { $emoji_language } <b>Language</b>

    Choose the interface language:

code-invalid = { $emoji_x } Code not found. Check it and try again.
code-banned = { $emoji_no_entry_sign } Your account has been banned by an administrator. Please contact support.
code-locked = { $emoji_shield } Too many wrong attempts in a row. Please try entering the code again later.
code-already-added = { $emoji_white_check_mark } This code is already linked to your account.
code-accepted = { $emoji_white_check_mark } <b>Code accepted!</b>
code-prompt-again = Enter another access code.

rate-limited = { $emoji_shield } You're going too fast — please slow down.

link-header = { $emoji_key } <b>Your subscriptions</b>
link-choose-prompt = Choose a subscription:
link-detail-header =
    { $emoji_rocket } <b>{ $code }</b>

    { $emoji_format_quote } { $description } { $emoji_format_quote }
link-help-hint = Run /help to see how to use your subscription.
link-none = You don't have any subscriptions yet. Tap "Enter code" to get access.
link-banned-notice = { $emoji_no_entry_sign } <b>Your subscription has been blocked by an administrator.</b>
link-btn-unsubscribe = Give up this subscription
link-unsubscribe-confirm =
    { $emoji_no_entry_sign } <b>Give up subscription "{ $code }"?</b>

    { $description }

    Access will be revoked immediately. To use this subscription again you'll need to enter its code once more.
link-btn-unsubscribe-confirm = Yes, give it up
link-btn-unsubscribe-cancel = No, keep it
link-unsubscribed-done = { $emoji_white_check_mark } You gave up this subscription. Access has been revoked.

sub-expiry-normal = Subscription: until { $date }
sub-expiry-eternal = Subscription: unlimited { $emoji_infinity }
sub-traffic-normal = { $used } / { $limit } GB
sub-traffic-unlimited = { $used } GB / { $emoji_infinity }

help-text =
    <b>Available commands</b>

    /start — start using the bot
    /help — show this message
    /link — get your subscriptions
    /code — enter another code

help-admin-suffix =
    <b>Admin commands</b>

    /admin — open the admin panel

unknown-command = Unknown command. Send /help to see the list of available commands.
unknown-message = I don't understand this message. Send /code to enter an access code.

broadcast-prefix = { $emoji_loudspeaker } <b>Message from the administration</b>

yes = Yes
no = No

### Admin panel

admin-only = This command is available to administrators only.
admin-menu-title =
    { $emoji_gear } <b>Admin panel</b>

    Choose an action:
admin-btn-create-code = Create code
admin-btn-codes = All codes
admin-btn-users = Users
admin-btn-admins = Admins
admin-btn-broadcast = Broadcast
admin-btn-squads = Squads
admin-btn-close = Back
admin-btn-back = Back
admin-btn-prev = Prev
admin-btn-next = Next
admin-btn-cancel = Cancel
admin-btn-confirm = Confirm
admin-btn-done = Done
admin-btn-undo = Undo last
admin-btn-skip = Skip
form-btn-leave-empty = Leave empty

admin-create-code-prompt-code = Enter a new code (letters, digits, "-" or "_", 8 to 32 characters):
admin-create-code-invalid = Invalid code format. Use letters, digits, "-" or "_", 8 to 32 characters long.
admin-create-code-exists = This code already exists. Enter another one.
admin-create-code-prompt-link = Send a link. You can add several — this message reappears after each one.
admin-create-code-links-added = Links added: { $count }
admin-create-code-link-name-prompt = Enter a name for this link (optional):
admin-create-code-prompt-description = Enter a description for the subscription:
admin-create-code-choose-squad-prompt = Choose a Squad for this Remnawave link:
admin-create-code-squads-empty = No Squads available — create one in the Squads admin screen, or every existing Squad is already used here.
admin-create-code-squad-item = { $name }
admin-create-code-done = { $emoji_white_check_mark } Code "{ $code }" created.

admin-page-indicator = · { $page }/{ $total }
admin-codes-title = { $emoji_package } <b>Codes</b> ({ $count })
admin-codes-empty = There are no codes yet.
admin-codes-item = { $code }
admin-code-detail-title =
    { $emoji_package } <b>{ $code }</b>

    Subscription: { $description }
admin-code-links-count = Links: { $count }
admin-btn-manage-links = Links
admin-code-links-title = { $emoji_link } <b>Links — { $code }</b>
admin-code-no-links = No links yet.
admin-code-link-removed = Link removed.
admin-code-link-row = { $type } — { $value }
admin-code-link-row-named = { $name } ({ $type }) — { $value }
admin-code-link-row-disabled = { $emoji_no_entry_sign } { $row } (disabled)
admin-code-link-type-fix = fix
admin-code-link-type-remnawave = remnawave
admin-code-link-squad-missing = No Squad chosen, or it was deleted
admin-btn-add-link = Add link
admin-btn-add-remnawave-link = Add Remnawave link
admin-code-add-link-type-prompt = Choose the type of link to add:
admin-btn-link-type-fix = Fixed link
admin-btn-link-type-remnawave = Remnawave link
admin-code-link-detail-title = { $emoji_link } <b>Link #{ $n } — { $code }</b>
admin-btn-replace-link = Replace link
admin-code-replace-link-prompt = Send a new URL to replace the current one.
admin-code-link-replaced = { $emoji_white_check_mark } Link updated.
admin-btn-rename-link = Rename
admin-code-link-renamed = { $emoji_white_check_mark } Link renamed.
admin-btn-move-up = ↑ Move up
admin-btn-move-down = ↓ Move down
admin-btn-disable-link = Disable link
admin-btn-enable-link = Enable link
admin-code-link-disabled-done = Link disabled. It's no longer visible to users.
admin-code-link-enabled-done = Link enabled again.
admin-btn-delete-link = Delete link
admin-btn-edit-code = Rename code
admin-btn-edit-description = Edit description
admin-btn-delete-code = Delete code
admin-code-add-link-prompt = Send a new fixed link for this code.
admin-code-link-added = { $emoji_white_check_mark } Link added.
admin-code-link-name-prompt = Send a name for this link (optional):
admin-code-edit-name-prompt = Send a new name for this code (letters, digits, "-" or "_", 8 to 32 characters). Everyone who already has this code keeps their access under the new name.
admin-code-renamed = { $emoji_white_check_mark } Code "{ $old }" renamed to "{ $new }".
admin-code-edit-description-prompt = Send a new description.
admin-code-description-updated = { $emoji_white_check_mark } Description updated.
admin-code-deleted = Code "{ $code }" and all its links have been deleted.
admin-btn-disable-remnawave = Disable Remnawave
admin-btn-enable-remnawave = Enable Remnawave
admin-code-remnawave-disabled-done = { $emoji_no_entry_sign } Remnawave disabled for code "{ $code }".
admin-code-remnawave-enabled-done = { $emoji_white_check_mark } Remnawave enabled for code "{ $code }".

admin-squads-title = { $emoji_shield } <b>Squads</b> ({ $count })
admin-squads-empty = There are no Squads yet.
admin-squads-item = { $name } [{ $server }]
admin-btn-create-squad = Create Squad
admin-squad-create-choose-server-prompt = Choose a Remnawave server for the new Squad:
admin-squad-server-item = { $server }
admin-squad-create-prompt-name = Enter a name for the Squad (server: { $server }):
admin-squad-name-invalid = The name can't be empty.
admin-squad-create-prompt-internal-squads = Choose the Remnawave internal squads to include in this Squad:
admin-squad-internal-squads-empty = No internal squads found on that Remnawave server.
admin-squad-internal-squad-item = { $name }
admin-squad-created-done = { $emoji_white_check_mark } Squad "{ $name }" created.
admin-squad-detail-title = { $emoji_shield } <b>{ $name }</b>
admin-squad-detail-server = Server: { $server }
admin-squad-detail-count = Internal squads: { $count }
admin-btn-edit-squad-name = Rename
admin-btn-edit-squad-internal-squads = Edit internal squads
admin-btn-delete-squad = Delete Squad
admin-squad-edit-name-prompt = Send a new name for the Squad (server: { $server }):
admin-squad-renamed = { $emoji_white_check_mark } Squad renamed.
admin-squad-edit-internal-squads-prompt = Choose the Remnawave internal squads for this Squad:
admin-squad-internal-squads-updated = { $emoji_white_check_mark } Internal squads updated.
admin-squad-deleted-done = { $emoji_white_check_mark } Squad deleted. Links that pointed to it will stop granting access — remove them from their codes.

admin-users-title = { $emoji_bust_in_silhouette } <b>Users</b> ({ $count })
admin-users-empty = There are no users yet.
admin-users-item = { $name } (id { $id }) — codes: { $count }
admin-user-detail-title =
    { $emoji_bust_in_silhouette } <b>{ $name }</b>

    ID: <code>{ $id }</code>
    Blocked: { $banned }
admin-user-codes-none = This user has no activated codes.
admin-btn-subscriptions = Subscriptions ({ $count })
admin-user-subscriptions-title = { $emoji_key } <b>Subscriptions for user { $id }</b>
admin-user-revoke-btn = Revoke "{ $code }"
admin-user-revoke-done = Code "{ $code }" revoked from user { $id }.
admin-user-ban-btn = Block user
admin-user-unban-btn = Unblock user
admin-user-ban-admin-denied = Can't block an administrator. Revoke their admin rights first, in the Administrators section.
admin-user-remnawave-linked = Remnawave [{ $server }]: { $username } ({ $source })
admin-user-remnawave-link-source-auto = auto
admin-user-remnawave-link-source-manual = manual
admin-btn-link-remnawave = Link Remnawave
admin-btn-link-remnawave-server = Link: { $server }
admin-btn-unlink-remnawave-server = Unlink: { $server }
admin-user-remnawave-unlinked-done = { $emoji_white_check_mark } Remnawave account unlinked from user { $id }.
admin-user-remnawave-disabled-done = { $emoji_no_entry_sign } Remnawave disabled for user { $id }.
admin-user-remnawave-enabled-done = { $emoji_white_check_mark } Remnawave enabled for user { $id }.
admin-link-remnawave-choose-server-prompt = Choose a Remnawave server:
admin-link-remnawave-prompt = Enter the Remnawave username to link to id { $id } (server { $server }):
admin-link-remnawave-not-found = No Remnawave user with that username was found.
admin-link-remnawave-lookup-failed = Couldn't reach Remnawave. Please try again.
admin-link-remnawave-confirm =
    Link Remnawave account "{ $username }" to user id { $id }?

    { $url }
admin-link-remnawave-done = { $emoji_white_check_mark } Remnawave account linked to user { $id }.

admin-admins-title = { $emoji_shield } <b>Administrators</b> ({ $count })
admin-admins-item = { $name } (id { $id })
admin-btn-add-admin = Add administrator
admin-add-admin-choose-method-prompt = How should the new administrator be specified?
admin-add-admin-method-id = By ID
admin-add-admin-method-username = By username
admin-add-admin-prompt = Send the numeric Telegram ID of the new administrator.
admin-add-admin-invalid = Invalid ID. Send a number — the user's Telegram ID.
admin-add-admin-prompt-username = Send the user's username (with or without @). The user must have started the bot at least once.
admin-add-admin-username-invalid = No user with that username was found. They may not have started the bot yet — use their numeric ID instead.
admin-add-admin-already = This user is already an administrator.
admin-add-admin-done = { $emoji_white_check_mark } User { $id } is now an administrator.
admin-remove-admin-btn = Revoke rights — { $name }
admin-remove-admin-done = Administrator rights revoked from user { $id }.

admin-btn-add-user = Add user
admin-add-user-prompt = Send the user's Telegram ID or username (with or without @).
admin-add-user-invalid = User not found. If they haven't started the bot yet, use their numeric ID instead.
admin-add-user-subs-title = Choose which subscriptions to enable for { $name } (id { $id }):
admin-add-user-subs-empty = There are no codes yet. Create one first, in the Codes section.
admin-add-user-sub-item = { $code } — { $description }
admin-add-user-done = { $emoji_white_check_mark } User { $id } added. Subscriptions enabled: { $count }.

admin-broadcast-target-prompt = { $emoji_loudspeaker } Who should receive the message?
admin-broadcast-target-all = All users
admin-broadcast-target-code = By code
admin-broadcast-choose-code = Choose a code:
admin-broadcast-no-codes = There are no codes yet.
admin-broadcast-prompt-content = Send the text, photo, video, document, audio, voice message, video note, or sticker to broadcast. Formatting and custom emoji are supported.
admin-broadcast-edit-title-btn = Edit title
admin-broadcast-title-prompt =
    Current title:
    <code>{ $current_title }</code>

    Send a new title (formatting is supported), or pick an action below.
admin-broadcast-title-empty-btn = Empty title
admin-broadcast-confirm =
    { $emoji_loudspeaker } Send this message to { $count } users?

    { $preview }
admin-broadcast-done = { $emoji_white_check_mark } Broadcast finished: { $sent } delivered.{ $failures }
admin-broadcast-empty = No recipients for this broadcast.

admin-broadcast-fail-never-started = { $count } users did not receive the message because they have never started the bot.
admin-broadcast-fail-blocked = { $count } users did not receive the message because they have blocked the bot.
admin-broadcast-fail-deactivated = { $count } users did not receive the message because their accounts were deleted or deactivated.
admin-broadcast-fail-other = { $count } users did not receive the message for another reason.

admin-broadcast-type-photo = Photo
admin-broadcast-type-video = Video
admin-broadcast-type-animation = GIF
admin-broadcast-type-document = Document
admin-broadcast-type-audio = Audio
admin-broadcast-type-voice = Voice message
admin-broadcast-type-video-note = Video note
admin-broadcast-type-sticker = Sticker
admin-broadcast-type-other = Content

### Webhook

admin-webhook-fallback-notice =
    ⚠️ The webhook stopped delivering updates - the bot automatically switched back to long polling.

    Telegram's last error: { $error }
