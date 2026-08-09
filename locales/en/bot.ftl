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
code-already-added = { $emoji_white_check_mark } This code is already linked to your account.
code-accepted = { $emoji_white_check_mark } <b>Code accepted!</b>
code-prompt-again = Enter another access code.

link-header = { $emoji_key } <b>Your subscriptions</b>
link-choose-prompt = Choose a subscription:
link-detail-header =
    { $emoji_small_blue_diamond } <b>{ $code }</b>

    { $emoji_format_quote } { $description } { $emoji_format_quote }
link-help-hint = Run /help to see how to use your subscription.
link-none = You don't have any subscriptions yet. Tap "Enter code" to get access.
link-banned-notice = { $emoji_no_entry_sign } <b>Your subscription has been blocked by an administrator.</b>

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
admin-create-code-prompt-squads = Choose the Remnawave squads to grant on activation of this code (optional, can be skipped):
admin-create-code-squads-empty = Remnawave squads aren't available — the code will be created with fixed links only.
admin-create-code-squad-item = { $name }
admin-create-code-done = { $emoji_white_check_mark } Code "{ $code }" created.

admin-page-indicator = · { $page }/{ $total }
admin-codes-title = { $emoji_package } <b>Codes</b> ({ $count })
admin-codes-empty = There are no codes yet.
admin-codes-item = { $code } — { $description } ({ $count } links)
admin-code-detail-title =
    { $emoji_package } <b>{ $code }</b>

    Subscription: { $description }
admin-code-no-links = No links yet.
admin-code-remove-link-btn = Remove link #{ $n }
admin-code-link-removed = Link removed.
admin-code-link-row = { $type } — { $value }
admin-code-link-row-named = { $name } ({ $type }) — { $value }
admin-code-link-type-fix = fix
admin-code-link-type-remnawave = remnawave
admin-code-link-remnawave-value = Remnawave subscription link
admin-btn-add-link = Add fixed link
admin-btn-add-remnawave-link = Add Remnawave link
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
admin-code-squads-count = Remnawave squads: { $count }
admin-btn-edit-squads = Remnawave squads
admin-code-edit-squads-prompt = Choose the Remnawave squads for this code:
admin-code-squads-updated = { $emoji_white_check_mark } Squads updated.
admin-btn-disable-remnawave = Disable Remnawave
admin-btn-enable-remnawave = Enable Remnawave
admin-code-remnawave-disabled-done = { $emoji_no_entry_sign } Remnawave disabled for code "{ $code }".
admin-code-remnawave-enabled-done = { $emoji_white_check_mark } Remnawave enabled for code "{ $code }".

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
admin-user-remnawave-linked = Remnawave account: { $username } ({ $source })
admin-user-remnawave-link-source-auto = auto
admin-user-remnawave-link-source-manual = manual
admin-btn-link-remnawave = Link Remnawave
admin-btn-unlink-remnawave = Unlink Remnawave
admin-user-remnawave-unlinked-done = { $emoji_white_check_mark } Remnawave account unlinked from user { $id }.
admin-user-remnawave-disabled-done = { $emoji_no_entry_sign } Remnawave disabled for user { $id }.
admin-user-remnawave-enabled-done = { $emoji_white_check_mark } Remnawave enabled for user { $id }.
admin-link-remnawave-prompt = Enter the Remnawave username to link to id { $id }:
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
