import asyncio
import html
import sqlite3
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from aiohttp import web

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ADMINS = -1004396371396
ADMIN_IDS = [7912018121, 807512049, 1709727241, 922576013, 5966724057, 755639362, 895799049]

PREMIUM_EMOJIS = {
    "angel_left": "5314416167828356312",
    "angel_right": "5314267347211551147",
    "greet_icon": "5312440122094947354",
    "registered_already": "5301029983127369647",
    "report_header": "5289572492145346795",
    "num_1": "5424922364934644955",
    "num_2": "5425099351946979074",
    "num_3": "5424789800769050978",
    "sparkles": "5406735098286453901",
    "heart": "5406700120072797432",
    "flower": "5408837832670195631",
    "star": "5409376309899964471",
    "ribbon": "5408866334073173070",
    "dove": "5314416167828356312",
    "register_icon": "5424672977658603170",
    "idea_icon": "5425077301584882153",
    "support_icon": "5425016630876863272",
    "notifications_icon": "5427255210781208287",
    "report_icon": "5424913530186919433",
    "help_icon": "5424877482526401489",
    "idea_discuss": "5251488342821863423",
    "idea_voice": "5246755980351408295",
    "support_header": "5289540825351473897",
    "always_near": "5407096682993170829",
    "check_icon": "5425109908976590072",
    "cross_icon": "5425061375846147731",
    "edit_icon": "5424833446058935532"
}

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())
conn = sqlite3.connect("club_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    game_nick TEXT,
    registered_at TEXT,
    subscribed INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    msg_in_admins TEXT
)
""")
conn.commit()

class Registration(StatesGroup):
    waiting_for_nick = State()
    waiting_for_new_nick = State()

def e(key, fallback="✨"):
    return f'<tg-emoji emoji-id="{PREMIUM_EMOJIS[key]}">{fallback}</tg-emoji>'

def main_menu(is_registered=False):
    buttons = []
    if not is_registered:
        buttons.append([InlineKeyboardButton(text="Зарегистрироваться", callback_data="register", icon_custom_emoji_id=PREMIUM_EMOJIS["register_icon"])])
    else:
        buttons.append([InlineKeyboardButton(text="Изменить игровой ник", callback_data="change_nick", icon_custom_emoji_id=PREMIUM_EMOJIS["edit_icon"])])
    
    buttons.extend([
        [InlineKeyboardButton(text="Сообщить о пропуске актива / кубков", callback_data="report_active", icon_custom_emoji_id=PREMIUM_EMOJIS["report_icon"])],
        [InlineKeyboardButton(text="Сообщить о замене / опоздании на челлендж", callback_data="report_challenge", icon_custom_emoji_id=PREMIUM_EMOJIS["report_icon"])],
        [InlineKeyboardButton(text="Предложить идею", callback_data="idea", icon_custom_emoji_id=PREMIUM_EMOJIS["idea_icon"])],
        [InlineKeyboardButton(text="Связаться с админами", callback_data="support", icon_custom_emoji_id=PREMIUM_EMOJIS["support_icon"])],
        [InlineKeyboardButton(text="Уведомления", callback_data="notifications", icon_custom_emoji_id=PREMIUM_EMOJIS["notifications_icon"])],
        [InlineKeyboardButton(text="Помощь", callback_data="help", icon_custom_emoji_id=PREMIUM_EMOJIS["help_icon"])]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def notifications_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Включить", callback_data="subscribe", icon_custom_emoji_id=PREMIUM_EMOJIS["notifications_icon"]),
            InlineKeyboardButton(text="Выключить", callback_data="unsubscribe", icon_custom_emoji_id=PREMIUM_EMOJIS["help_icon"])
        ],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
    ])

def report_active_text():
    return (
        f"{e('report_header')} <b>Сообщить о пропуске актива / кубков</b>\n\n"
        f"Напиши одним сообщением:\n"
        f"{e('num_1')} Игровой ник\n"
        f"{e('num_2')} Не успеешь сделать норму актива или кубков\n"
        f"{e('num_3')} Причину\n\n"
        f"{e('sparkles')} <i>Пример:</i>\n"
        f"wqxsvkb, не смогу выполнить норму актива завтра, причина: работаю\n\n"
    )

def report_challenge_text():
    return (
        f"{e('report_header')} <b>Сообщить о замене / опоздании на челлендж</b>\n\n"
        f"Напиши одним сообщением:\n"
        f"{e('num_1')} Игровой ник\n"
        f"{e('num_2')} Не сможешь выполнить челлендж\n"
        f"{e('num_3')} Причину\n\n"
        f"{e('sparkles')} <i>Пример:</i>\n"
        f"blythedoll, не смогу приять участие в челлендже завтра, причина: уезжаю\n\n"
    )

def idea_text():
    return (
        f"{e('flower')} <b>Поделись идеей!</b>\n\n"
        f"Есть предложение для клуба?\n"
        f"Напиши — мы всё обсудим {e('idea_discuss')}\n\n"
        f"Твоё мнение важно для нас! {e('idea_voice')}"
    )

def support_text():
    return (
        f"{e('support_header')} <b>Связаться с админами</b>\n\n"
        f"Напиши свой вопрос или проблему.\n"
        f"Администрация свяжется в ближайшее время {e('star')}\n\n"
        f"Мы всегда рядом {e('always_near')}"
    )

def help_text():
    return (
        f"{e('heart')} <b>Команды бота</b> {e('dove')}\n\n"
        f"{e('sparkles')} /start — главное меню\n"
        f"{e('register_icon')} /register — регистрация\n"
        f"{e('edit_icon')} /change_nick — сменить игровой ник\n"
        f"{e('report_icon')} /report_active — пропуск актива / кубков\n"
        f"{e('report_icon')} /report_challenge — замена / опоздание на челлендж\n"
        f"{e('idea_icon')} /idea — предложить идею\n"
        f"{e('support_icon')} /support — связаться с админами\n"
        f"{e('notifications_icon')} /notifications — уведомления\n"
        f"{e('notifications_icon')} /subscribe — включить уведомления\n"
        f"{e('help_icon')} /unsubscribe — выключить уведомления\n"
        f"{e('help_icon')} /help — список команд"
    )

async def send_menu(chat_id, text, is_registered=False):
    await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu(is_registered))

async def send_report(chat_id, text):
    await bot.send_message(chat_id, text, parse_mode="HTML")

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    cursor.execute("SELECT game_nick FROM users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if user:
        text = f"{e('greet_icon')} Привет, {html.escape(user[0])}! {e('sparkles')}\n\nТы в команде {e('angel_left')} <b>Freed Angels</b> {e('angel_right')}\nВыбери действие"
        await send_menu(message.chat.id, text, is_registered=True)
    else:
        text = f"{e('greet_icon')} Добро пожаловать в {e('angel_left')} <b>Freed Angels</b> {e('angel_right')}! {e('star')}\n\nЯ — твой личный помощник {e('ribbon')}\nВыбери действие"
        await send_menu(message.chat.id, text, is_registered=False)

@dp.message(Command("register"))
async def register_command(message: Message, state: FSMContext):
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (message.from_user.id,))
    if cursor.fetchone():
        await send_menu(message.chat.id, f"{e('registered_already')} Регистрация уже пройдена! {e('sparkles')}", is_registered=True)
        return
    await state.update_data(user_id=message.from_user.id, username=message.from_user.username or "без ника", full_name=message.from_user.full_name)
    await message.answer(f"{e('sparkles')} Напиши свой игровой ник из Аватарии\n\nПример: <i>Игрок</i>", parse_mode="HTML")
    await state.set_state(Registration.waiting_for_nick)

@dp.callback_query(F.data == "register")
async def register_button(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await register_command(callback.message, state)
    await callback.answer()

@dp.message(StateFilter(Registration.waiting_for_nick))
async def process_nick(message: Message, state: FSMContext):
    game_nick = (message.text or "").strip()
    if not game_nick or len(game_nick) > 50:
        await message.answer(f"{e('cross_icon')} Ник не может быть пустым или длиннее 50 символов.\nПопробуй ещё раз.", parse_mode="HTML")
        return
    data = await state.get_data()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, username, full_name, game_nick, registered_at, subscribed) VALUES (?, ?, ?, ?, ?, 1)", (data["user_id"], data["username"], data["full_name"], game_nick, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    await send_menu(message.chat.id, f"{e('check_icon')} Поздравляем, <b>{html.escape(game_nick)}</b>!\n\nТеперь ты в составе {e('angel_left')} <b>Freed Angels</b> {e('angel_right')}\n\nВсе функции доступны!", is_registered=True)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"{e('star')} <b>Новый участник в клубе!</b>\n\nИгровой ник: {html.escape(game_nick)}\nTelegram: @{html.escape(data['username'])}\nID: <code>{data['user_id']}</code>", parse_mode="HTML")
        except Exception:
            pass
    await state.clear()

@dp.message(Command("change_nick"))
@dp.callback_query(F.data == "change_nick")
async def change_nick_start(event, state: FSMContext):
    if isinstance(event, CallbackQuery):
        await event.message.delete()
        message = event.message
        user_id = event.from_user.id
    else:
        message = event
        user_id = message.from_user.id
    
    cursor.execute("SELECT game_nick FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer(f"{e('cross_icon')} Сначала нужно зарегистрироваться!", parse_mode="HTML")
        return

    await message.answer(f"{e('edit_icon')} Напиши свой новый игровой ник из Аватарии:", parse_mode="HTML")
    await state.set_state(Registration.waiting_for_new_nick)
    if isinstance(event, CallbackQuery):
        await event.answer()

@dp.message(StateFilter(Registration.waiting_for_new_nick))
async def process_new_nick(message: Message, state: FSMContext):
    new_nick = (message.text or "").strip()
    if not new_nick or len(new_nick) > 50:
        await message.answer(f"{e('cross_icon')} Ник не может быть пустым или длиннее 50 символов.\nПопробуй ещё раз.", parse_mode="HTML")
        return
    
    cursor.execute("UPDATE users SET game_nick = ? WHERE user_id = ?", (new_nick, message.from_user.id))
    conn.commit()
    
    await send_menu(message.chat.id, f"{e('check_icon')} Ник успешно изменён на <b>{html.escape(new_nick)}</b>!", is_registered=True)
    await state.clear()

@dp.message(Command("list"))
async def admin_list_users(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    cursor.execute("SELECT game_nick, username, user_id FROM users")
    users = cursor.fetchall()
    
    if not users:
        await message.answer(f"{e('cross_icon')} В базе пока нет участников.", parse_mode="HTML")
        return
    
    response = f"{e('star')} <b>Список участников клуба:</b>\n\n"
    for i, u in enumerate(users, 1):
        nick, tg, uid = u
        response += f"{i}. <b>{html.escape(nick)}</b> — @{html.escape(tg or 'нет')} (<code>{uid}</code>)\n"
    
    response += f"\n{e('dove')} Всего: {len(users)}"
    
    if len(response) > 4000:
        for x in range(0, len(response), 4000):
            await message.answer(response[x:x+4000], parse_mode="HTML")
    else:
        await message.answer(response, parse_mode="HTML")

@dp.callback_query(F.data == "report_active")
async def report_active_button(callback: CallbackQuery):
    await callback.message.delete()
    await send_report(callback.message.chat.id, report_active_text())
    await callback.answer()

@dp.message(Command("report_active"))
async def report_active_command(message: Message):
    await send_report(message.chat.id, report_active_text())

@dp.callback_query(F.data == "report_challenge")
async def report_challenge_button(callback: CallbackQuery):
    await callback.message.delete()
    await send_report(callback.message.chat.id, report_challenge_text())
    await callback.answer()

@dp.message(Command("report_challenge"))
async def report_challenge_command(message: Message):
    await send_report(message.chat.id, report_challenge_text())

@dp.callback_query(F.data == "idea")
async def idea_button(callback: CallbackQuery):
    await callback.message.delete()
    await send_report(callback.message.chat.id, idea_text())
    await callback.answer()

@dp.message(Command("idea"))
async def idea_command(message: Message):
    await send_report(message.chat.id, idea_text())

@dp.callback_query(F.data == "support")
async def support_button(callback: CallbackQuery):
    await callback.message.delete()
    await send_report(callback.message.chat.id, support_text())
    await callback.answer()

@dp.message(Command("support"))
async def support_command(message: Message):
    await send_report(message.chat.id, support_text())

@dp.callback_query(F.data == "notifications")
async def notifications_button(callback: CallbackQuery):
    await callback.message.delete()
    await bot.send_message(callback.message.chat.id, f"{e('star')} <b>Уведомления</b>\n\nХочешь получать уведомления о событиях клуба?", parse_mode="HTML", reply_markup=notifications_menu())
    await callback.answer()

@dp.message(Command("notifications"))
async def notifications_command(message: Message):
    await bot.send_message(message.chat.id, f"{e('star')} <b>Уведомления</b>\n\nХочешь получать уведомления о событиях клуба?", parse_mode="HTML", reply_markup=notifications_menu())

@dp.callback_query(F.data == "subscribe")
async def subscribe_button(callback: CallbackQuery):
    cursor.execute("UPDATE users SET subscribed = 1 WHERE user_id = ?", (callback.from_user.id,))
    conn.commit()
    await send_menu(callback.message.chat.id, f"{e('check_icon')} Подписка включена! {e('sparkles')}", is_registered=True)
    await callback.answer()

@dp.message(Command("subscribe"))
async def subscribe_command(message: Message):
    cursor.execute("UPDATE users SET subscribed = 1 WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await send_menu(message.chat.id, f"{e('check_icon')} Подписка включена! {e('sparkles')}", is_registered=True)

@dp.callback_query(F.data == "unsubscribe")
async def unsubscribe_button(callback: CallbackQuery):
    cursor.execute("UPDATE users SET subscribed = 0 WHERE user_id = ?", (callback.from_user.id,))
    conn.commit()
    await send_menu(callback.message.chat.id, f"{e('cross_icon')} Уведомления отключены.", is_registered=True)
    await callback.answer()

@dp.message(Command("unsubscribe"))
async def unsubscribe_command(message: Message):
    cursor.execute("UPDATE users SET subscribed = 0 WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await send_menu(message.chat.id, f"{e('cross_icon')} Уведомления отключены.", is_registered=True)

@dp.callback_query(F.data == "help")
async def help_button(callback: CallbackQuery):
    await callback.message.delete()
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (callback.from_user.id,))
    await send_menu(callback.message.chat.id, help_text(), is_registered=cursor.fetchone() is not None)
    await callback.answer()

@dp.message(Command("help"))
async def help_command(message: Message):
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (message.from_user.id,))
    await send_menu(message.chat.id, help_text(), is_registered=cursor.fetchone() is not None)

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.delete()
    cursor.execute("SELECT game_nick FROM users WHERE user_id = ?", (callback.from_user.id,))
    user = cursor.fetchone()
    if user:
        await send_menu(callback.message.chat.id, f"{e('dove')} <b>Главное меню</b>", is_registered=True)
    else:
        await send_menu(callback.message.chat.id, f"{e('dove')} <b>Главное меню</b>", is_registered=False)
    await callback.answer()

@dp.message(Command("broadcast"))
async def broadcast(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(f"{e('cross_icon')} Доступ запрещён.", parse_mode="HTML")
        return
    text = (message.text or "").replace("/broadcast", "", 1).strip()
    if not text:
        await message.answer("Использование: /broadcast Текст объявления")
        return
    cursor.execute("SELECT user_id FROM users WHERE subscribed = 1")
    users = cursor.fetchall()
    count = 0
    for (user_id,) in users:
        try:
            await bot.send_message(user_id, f"{e('dove')} <b>ОБЪЯВЛЕНИЕ КЛУБА</b>\n\n{html.escape(text)}", parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(f"{e('check_icon')} Отправлено: {count}", parse_mode="HTML")

@dp.message()
async def all_messages(message: Message):
    if message.chat.type == "private":
        user = message.from_user
        cursor.execute("SELECT game_nick FROM users WHERE user_id = ?", (user.id,))
        result = cursor.fetchone()
        game_nick = result[0] if result else "не указан"
        text = html.escape(message.text or "Сообщение без текста или медиафайл")
        card = f"{e('sparkles')} <b>Новое обращение</b>\n\nУчастник: {html.escape(user.full_name)}\nTelegram: @{html.escape(user.username or 'нет ника')}\nИгровой ник: {html.escape(game_nick)}\nID: <code>{user.id}</code>\n\nСообщение:\n{text}\n\nОтветьте на это сообщение, чтобы отправить ответ."
        sent = await bot.send_message(CHAT_ADMINS, card, parse_mode="HTML")
        cursor.execute("INSERT INTO messages (user_id, msg_in_admins) VALUES (?, ?)", (user.id, str(sent.message_id)))
        conn.commit()
        await message.reply(f"{e('check_icon')} Сообщение передано администрации.\n\nХочешь сделать что-то ещё?", reply_markup=main_menu(result is not None), parse_mode="HTML")
    elif message.chat.id == CHAT_ADMINS and message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        cursor.execute("SELECT user_id FROM messages WHERE msg_in_admins = ? ORDER BY id DESC LIMIT 1", (str(message.reply_to_message.message_id),))
        result = cursor.fetchone()
        if not result:
            await message.reply(f"{e('cross_icon')} Получатель не найден.", parse_mode="HTML")
            return
        reply_text = html.escape(message.text or "Сообщение без текста")
        try:
            sent = await bot.send_message(result[0], f"{e('dove')} <b>Ответ от администрации</b>\n\n{reply_text}", parse_mode="HTML")
            cursor.execute("INSERT INTO messages (user_id, msg_in_admins) VALUES (?, ?)", (result[0], str(message.message_id)))
            conn.commit()
            await message.reply(f"{e('check_icon')} Ответ доставлен.", parse_mode="HTML")
        except Exception:
            await message.reply(f"{e('cross_icon')} Не удалось отправить ответ.", parse_mode="HTML")

async def health_check(request):
    return web.Response(text="🕊 Бот Freed Angels работает!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Веб-сервер запущен на порту {port}")

async def main():
    print("🕊 Бот клуба Freed Angels успешно запущен!")
    await asyncio.gather(
        dp.start_polling(bot),
        start_web_server()
    )

if __name__ == "__main__":
    asyncio.run(main())
