import json
import time
import datetime
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def create_default_config():
    default_config = {
        "token": "YOUR_BOT_TOKEN",
        "super_admins": [],
        "admins": [],
        "blacklist": []
    }
    with open('conf.json', 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=4)
    return default_config

def load_config():
    try:
        if not os.path.exists('conf.json'):
            return create_default_config()
        with open('conf.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            required_fields = ['token', 'super_admins', 'admins', 'blacklist']
            for field in required_fields:
                if field not in config:
                    config[field] = []
            return config
    except json.JSONDecodeError:
        return create_default_config()

def save_config():
    with open('conf.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

config = load_config()

if config['token'] == "YOUR_BOT_TOKEN":
    print("⚠️ Пожалуйста, установите правильный токен бота в файле conf.json")
    exit(1)

# Инициализация бота
bot = Bot(token=config['token'])
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния FSM
class AdminStates(StatesGroup):
    waiting_for_reply = State()
    waiting_for_admin_id = State()
    waiting_for_admin_remove_id = State()
    waiting_for_blacklist_id = State()
    waiting_for_blacklist_remove_id = State()

# Глобальные переменные
bot_active = True
start_time = time.time()
users_data = {
    'users': set(),
    'messages_count': 0
}

# Клавиатуры
admin_panel = InlineKeyboardMarkup(row_width=2)
admin_panel.add(
    InlineKeyboardButton("🔄 Старт/Стоп бот", callback_data="bot_toggle"),
    InlineKeyboardButton("👮 Админ", callback_data="admin_manage"),
    InlineKeyboardButton("⛔️ ЧС", callback_data="blacklist"),
    InlineKeyboardButton("📊 Статистика", callback_data="stats")
)

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    users_data['users'].add(message.from_user.id)
    await message.answer(
        "👋 *Добро пожаловать!*\n\n"
        "✨ Я готов передавать ваши арты/вопросы/эдиты или другое творчество администраторам.\n"
        "📝 Просто напишите любое сообщение, и я его доставлю!",
        parse_mode="Markdown"
    )

@dp.message_handler(commands=['panel'])
async def panel_command(message: types.Message):
    if message.from_user.id not in config['super_admins']:
        await message.answer("⛔️ *У вас нет доступа к панели управления*", parse_mode="Markdown")
        return
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "✅ Активен" if bot_active else "⛔️ Приостановлен"
    
    await message.answer(
        f"🎛 *Панель управления*\n\n"
        f"🕒 Дата и время: `{current_time}`\n"
        f"📡 Статус бота: {status}",
        parse_mode="Markdown",
        reply_markup=admin_panel
    )

@dp.callback_query_handler(lambda c: c.data == "bot_toggle")
async def bot_toggle(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in config['super_admins']:
        await callback_query.answer("⛔️ Недостаточно прав", show_alert=True)
        return
    
    global bot_active
    bot_active = not bot_active
    status = "✅ активирован" if bot_active else "⛔️ приостановлен"
    
    await callback_query.message.edit_text(
        f"🤖 *Статус бота изменен*\n\n"
        f"Текущий статус: {status}",
        parse_mode="Markdown",
        reply_markup=admin_panel
    )

@dp.callback_query_handler(lambda c: c.data == "admin_manage")
async def admin_manage(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in config['super_admins']:
        await callback_query.answer("⛔️ Недостаточно прав", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin"),
        InlineKeyboardButton("➖ Убрать админа", callback_data="remove_admin")
    )
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_panel"))
    
    current_admins = "\n".join([f"👤 `{admin}`" for admin in config['admins']])
    await callback_query.message.edit_text(
        f"*👮 Управление администраторами*\n\n"
        f"Текущие администраторы:\n{current_admins or 'Список пуст'}",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == "stats")
async def show_stats(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in config['super_admins']:
        await callback_query.answer("⛔️ Недостаточно прав", show_alert=True)
        return
    
    uptime = time.time() - start_time
    uptime_hours = int(uptime // 3600)
    uptime_minutes = int((uptime % 3600) // 60)
    uptime_seconds = int(uptime % 60)
    
    # Получаем информацию о системе
    try:
        with open('/proc/meminfo') as f:
            mem_total = 0
            mem_available = 0
            for line in f:
                if 'MemTotal' in line:
                    mem_total = int(line.split()[1])
                elif 'MemAvailable' in line:
                    mem_available = int(line.split()[1])
                if mem_total and mem_available:
                    break
        mem_used_percent = ((mem_total - mem_available) / mem_total) * 100
    except:
        mem_used_percent = 0

    try:
        with open('/proc/loadavg') as f:
            load_avg = f.read().split()[0]
    except:
        load_avg = "N/A"
    
    # Вычисляем среднее количество сообщений на пользователя
    avg_messages = users_data['messages_count']/len(users_data['users']) if len(users_data['users']) > 0 else 0
    
    stats_text = (
        f"📊 *Статистика бота*\n\n"
        f"👥 Пользователей: `{len(users_data['users'])}`\n"
        f"👑 Супер админов: `{len(config['super_admins'])}`\n"
        f"👮 Админов: `{len(config['admins'])}`\n"
        f"⛔️ В ЧС: `{len(config['blacklist'])}`\n"
        f"📨 Всего сообщений: `{users_data['messages_count']}`\n\n"
        f"🤖 *Информация о боте:*\n"
        f"⏱ Время работы: `{uptime_hours}ч {uptime_minutes}м {uptime_seconds}с`\n"
        f"💻 Нагрузка системы: `{load_avg}`\n"
        f"💾 Использование RAM: `{mem_used_percent:.1f}%`\n"
        f"🌐 Пинг: `{int((time.time() - callback_query.message.date.timestamp()) * 1000)}ms`\n\n"
        f"📈 *Дополнительная статистика:*\n"
        f"📱 Активных диалогов: `{len(users_data['users'])}`\n"
        f"📊 Среднее кол-во сообщений на пользователя: `{avg_messages:.1f}`\n"
        f"🕒 Последний перезапуск: `{datetime.datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔄 Обновить", callback_data="stats"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_panel"))
    
    await callback_query.message.edit_text(
        stats_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == "blacklist")
async def blacklist_manage(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in config['super_admins']:
        await callback_query.answer("⛔️ Недостаточно прав", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("➕ Добавить в ЧС", callback_data="add_blacklist"),
        InlineKeyboardButton("➖ Убрать из ЧС", callback_data="remove_blacklist")
    )
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_panel"))
    
    blacklisted = "\n".join([f"🚫 `{user}`" for user in config['blacklist']])
    await callback_query.message.edit_text(
        f"*⛔️ Управление черным списком*\n\n"
        f"Пользователи в ЧС:\n{blacklisted or 'Список пуст'}",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == "add_blacklist")
async def add_blacklist_start(callback_query: types.CallbackQuery, state: FSMContext):
    await AdminStates.waiting_for_blacklist_id.set()
    await callback_query.message.edit_text(
        "📝 *Добавление в черный список*\n\n"
        "Отправьте ID пользователя для добавления в ЧС:",
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "remove_blacklist")
async def remove_blacklist_start(callback_query: types.CallbackQuery, state: FSMContext):
    await AdminStates.waiting_for_blacklist_remove_id.set()
    blacklisted = "\n".join([f"🚫 `{user}`" for user in config['blacklist']])
    await callback_query.message.edit_text(
        f"📝 *Удаление из черного списка*\n\n"
        f"Пользователи в ЧС:\n{blacklisted or 'Список пуст'}\n\n"
        f"Отправьте ID пользователя для удаления из ЧС:",
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "add_admin")
async def add_admin_start(callback_query: types.CallbackQuery, state: FSMContext):
    await AdminStates.waiting_for_admin_id.set()
    await callback_query.message.edit_text(
        "📝 *Добавление администратора*\n\n"
        "Отправьте ID пользователя для добавления в администраторы:",
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "remove_admin")
async def remove_admin_start(callback_query: types.CallbackQuery, state: FSMContext):
    await AdminStates.waiting_for_admin_remove_id.set()
    current_admins = "\n".join([f"👤 `{admin}`" for admin in config['admins']])
    await callback_query.message.edit_text(
        f"📝 *Удаление администратора*\n\n"
        f"Текущие администраторы:\n{current_admins or 'Список пуст'}\n\n"
        f"Отправьте ID администратора для удаления:",
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "back_to_panel")
async def back_to_panel(callback_query: types.CallbackQuery):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "✅ Активен" if bot_active else "⛔️ Приостановлен"
    
    await callback_query.message.edit_text(
        f"🎛 *Панель управления*\n\n"
        f"🕒 Дата и время: `{current_time}`\n"
        f"📡 Статус бота: {status}",
        parse_mode="Markdown",
        reply_markup=admin_panel
    )

@dp.message_handler(state=AdminStates.waiting_for_admin_id)
async def add_admin_finish(message: types.Message, state: FSMContext):
    try:
        admin_id = int(message.text)
        if admin_id in config['super_admins']:
            await message.answer("⚠️ Этот пользователь уже является супер-админом!")
        elif admin_id in config['admins']:
            await message.answer("⚠️ Этот пользователь уже является администратором!")
        else:
            config['admins'].append(admin_id)
            save_config()
            await message.answer("✅ Администратор успешно добавлен!")
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя!")
    await state.finish()

@dp.message_handler(state=AdminStates.waiting_for_admin_remove_id)
async def remove_admin_finish(message: types.Message, state: FSMContext):
    try:
        admin_id = int(message.text)
        if admin_id in config['super_admins']:
            await message.answer("⚠️ Невозможно удалить супер-админа!")
        elif admin_id in config['admins']:
            config['admins'].remove(admin_id)
            save_config()
            await message.answer("✅ Администратор успешно удален!")
        else:
            await message.answer("⚠️ Этот пользователь не является администратором!")
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя!")
    await state.finish()

@dp.message_handler(state=AdminStates.waiting_for_blacklist_id)
async def add_blacklist_finish(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        if user_id in config['super_admins'] or user_id in config['admins']:
            await message.answer("⚠️ Невозможно добавить администратора в черный список!")
        elif user_id in config['blacklist']:
            await message.answer("⚠️ Этот пользователь уже в черном списке!")
        else:
            config['blacklist'].append(user_id)
            save_config()
            await message.answer("✅ Пользователь успешно добавлен в черный список!")
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя!")
    await state.finish()

@dp.message_handler(state=AdminStates.waiting_for_blacklist_remove_id)
async def remove_blacklist_finish(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        if user_id in config['blacklist']:
            config['blacklist'].remove(user_id)
            save_config()
            await message.answer("✅ Пользователь успешно удален из черного списка!")
        else:
            await message.answer("⚠️ Этот пользователь не находится в черном списке!")
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя!")
    await state.finish()

@dp.message_handler()
async def handle_message(message: types.Message):
    if not bot_active:
        await message.answer("⛔️ *Работа бота приостановлена администратором*", parse_mode="Markdown")
        return
    
    if message.from_user.id in config['blacklist']:
        await message.answer("⛔️ *Вы находитесь в черном списке*", parse_mode="Markdown")
        return
    
    users_data['messages_count'] += 1
    
    admin_message = (
        f"📨 *Новое сообщение от пользователя:*\n\n"
        f"👤 ID: `{message.from_user.id}`\n"
        f"📝 Имя: [{message.from_user.full_name}](tg://user?id={message.from_user.id})\n"
        f"🔤 Username: @{message.from_user.username or 'отсутствует'}\n\n"
        f"💬 Текст:\n`{message.text}`"
    )
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("↩️ Ответить", callback_data=f"reply_{message.from_user.id}"))
    
    for admin_id in set(config['super_admins'] + config['admins']):
        try:
            await bot.send_message(
                admin_id,
                admin_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        except:
            continue
    
    await message.answer(
        "✅ *Сообщение отправлено администратору*\n_Ожидайте ответа_",
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data.startswith('reply_'))
async def reply_to_user(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = int(callback_query.data.split('_')[1])
    await state.update_data(reply_to=user_id)
    await AdminStates.waiting_for_reply.set()
    await callback_query.message.reply(
        "📝 *Введите ответ пользователю:*",
        parse_mode="Markdown"
    )

@dp.message_handler(state=AdminStates.waiting_for_reply)
async def process_reply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('reply_to')
    
    try:
        await bot.send_message(
            user_id,
            f"📨 *Ответ от администратора:*\n\n"
            f"{message.text}",
            parse_mode="Markdown"
        )
        await message.answer("✅ *Ответ успешно отправлен пользователю*", parse_mode="Markdown")
    except Exception as e:
        await message.answer("❌ *Ошибка отправки сообщения*", parse_mode="Markdown")
    
    await state.finish()

if __name__ == '__main__':
    from aiogram import executor
    print("🤖 Бот запущен...")
    executor.start_polling(dp, skip_updates=True)
