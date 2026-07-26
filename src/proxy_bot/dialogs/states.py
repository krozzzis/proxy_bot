from aiogram.fsm.state import State, StatesGroup


class UserMenu(StatesGroup):
    main = State()
    enter_code = State()
    links = State()
    help = State()


class AdminMenu(StatesGroup):
    main = State()


class AdminCreateCode(StatesGroup):
    enter_code = State()
    enter_links = State()
    enter_description = State()


class AdminUsers(StatesGroup):
    list = State()
    detail = State()


class AdminCodes(StatesGroup):
    list = State()
    detail = State()
    enter_link = State()
    edit_description = State()


class AdminAdmins(StatesGroup):
    list = State()
    enter_id = State()


class AdminBroadcast(StatesGroup):
    choose_target = State()
    choose_code = State()
    enter_text = State()
    confirm = State()
