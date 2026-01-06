from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from firebase_db import firebase_db
from keyboards import (
    get_admin_keyboard, 
    get_main_keyboard,
    get_admin_users_keyboard,
    get_admin_balance_keyboard,
    get_admin_hosting_keyboard,
    get_admin_promo_keyboard,
    get_admin_back_keyboard
)
from config import ADMIN_ID, HOSTING_PLANS
from utils.script_runner import script_runner
from datetime import datetime, timedelta
import os
import aiofiles
import shutil
import zipfile
import base64
from utils.file_processing import file_processor

router = Router()

class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_balance_amount = State()
    waiting_hosting_price = State()
    waiting_hosting_duration = State()
    waiting_promo_code = State()
    waiting_promo_type = State()
    waiting_promo_value = State()
    waiting_promo_limit = State()
    waiting_admin_user_id = State()
    waiting_admin_level = State()
    waiting_connect_bot = State()
    connected_bot_state = State()  # Новое состояние для подключенного бота

# Глобальная переменная для хранения подключенных ботов
connected_bots = {}

def check_admin_access(user_id, permission=None):
    """Проверка прав доступа - УПРОЩЕННАЯ ВЕРСИЯ"""
    user_data = firebase_db.get_user(str(user_id))
    if not user_data:
        return False
    
    # Если пользователь - владелец (указан в config)
    if user_id == ADMIN_ID:
        return True
    
    # Если пользователь админ в базе
    if user_data.get('is_admin') and user_data.get('admin_level', 0) > 0:
        return True
    
    return False

@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not check_admin_access(user_id):
        await message.answer("❌ Доступ запрещен")
        return
    
    # Выходим из режима подключенного бота если был
    if user_id in connected_bots:
        del connected_bots[user_id]
        await state.clear()
    
    user_data = firebase_db.get_user(str(user_id))
    admin_level = user_data.get('admin_level', 0) if user_data else 0
    
    # Если это владелец из config, но нет в базе - создаем запись
    if user_id == ADMIN_ID and (not user_data or not user_data.get('is_admin')):
        firebase_db.update_user(str(user_id), {
            'is_admin': True,
            'admin_level': 3
        })
        admin_level = 3
    
    await state.clear()
    
    level_text = ""
    if admin_level == 3:
        level_text = "👑 Владелец"
    elif admin_level == 2:
        level_text = "⚡ Админ" 
    elif admin_level == 1:
        level_text = "🛡️ Модератор"
    else:
        level_text = "👤 Админ"
    
    await message.answer(f"👨‍💻 Панель администратора | {level_text}", reply_markup=get_admin_keyboard(admin_level))

@router.message(F.text == "🤖 Подключиться к боту")
async def connect_bot_handler(message: Message, state: FSMContext):
    """Подключиться к другому боту пользователя"""
    user_id = message.from_user.id
    
    if not check_admin_access(user_id):
        await message.answer("❌ Недостаточно прав")
        return
    
    await state.set_state(AdminStates.waiting_connect_bot)
    await message.answer(
        "🤖 <b>Подключение к боту пользователя</b>\n\n"
        "Введите ID пользователя для подключения:",
        parse_mode="HTML",
        reply_markup=get_admin_back_keyboard()
    )

@router.message(AdminStates.waiting_connect_bot)
async def process_connect_bot(message: Message, state: FSMContext):
    """Обработка подключения к боту"""
    try:
        target_user_id = int(message.text.strip())
        
        target_user_data = firebase_db.get_user(str(target_user_id))
        if not target_user_data:
            await message.answer("❌ Пользователь не найден")
            return
        
        # Сохраняем информацию о подключенном боте
        connected_bots[message.from_user.id] = target_user_id
        await state.set_state(AdminStates.connected_bot_state)
        await state.update_data(connected_bot_id=target_user_id)
        
        # Получаем основную клавиатуру пользователя
        main_keyboard = get_main_keyboard(target_user_data)
        
        await message.answer(
            f"✅ <b>Подключено к боту пользователя</b>\n\n"
            f"👤 Пользователь: {target_user_data.get('first_name', 'Неизвестно')}\n"
            f"🆔 ID: {target_user_id}\n"
            f"🚀 Хостинг: {target_user_data.get('hosting_plan', 'Нет')}\n"
            f"💳 Баланс: {target_user_data.get('balance', 0)}₽\n\n"
            f"<b>Теперь вы можете управлять этим ботом. Все действия будут выполняться от имени этого пользователя.</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard
        )
        
    except ValueError:
        await message.answer("❌ Введите корректный ID пользователя")

# Перехватываем все сообщения когда админ подключен к боту
@router.message(AdminStates.connected_bot_state)
async def handle_connected_bot_actions(message: Message, state: FSMContext):
    """Обработка действий в подключенном боте"""
    admin_id = message.from_user.id
    
    if admin_id not in connected_bots:
        await state.clear()
        return
    
    target_user_id = connected_bots[admin_id]
    target_user_data = firebase_db.get_user(str(target_user_id))
    
    if not target_user_data:
        await message.answer("❌ Пользователь не найден")
        del connected_bots[admin_id]
        await state.clear()
        return
    
    # Обрабатываем команды как будто мы целевой пользователь
    if message.text == "🚀 Запустить":
        from handlers.hosting import start_script_handler
        # Временно подменяем user_id
        original_from_user = message.from_user
        message.from_user.id = target_user_id
        await start_script_handler(message)
        message.from_user = original_from_user
        
    elif message.text == "⏹️ Стоп":
        from handlers.hosting import stop_script_handler
        original_from_user = message.from_user
        message.from_user.id = target_user_id
        await stop_script_handler(message)
        message.from_user = original_from_user
        
    elif message.text == "📊 Ресурсы":
        from handlers.hosting import resources_handler
        original_from_user = message.from_user
        message.from_user.id = target_user_id
        await resources_handler(message)
        message.from_user = original_from_user
        
    elif message.text == "📁 Файлы":
        from handlers.files import files_handler
        original_from_user = message.from_user
        message.from_user.id = target_user_id
        await files_handler(message)
        message.from_user = original_from_user
        
    elif message.text == "👤 Профиль":
        from handlers.profile import profile_handler
        original_from_user = message.from_user
        message.from_user.id = target_user_id
        await profile_handler(message)
        message.from_user = original_from_user
        
    elif message.text == "🔙 Главное меню":
        # Возвращаемся в админ-панель
        del connected_bots[admin_id]
        await state.clear()
        user_data = firebase_db.get_user(str(admin_id))
        admin_level = user_data.get('admin_level', 0) if user_data else 0
        await message.answer("👨‍💻 Панель администратора", reply_markup=get_admin_keyboard(admin_level))
        
    elif message.text and message.text.startswith('/admin'):
        # Возвращаемся в админ-панель
        del connected_bots[admin_id]
        await state.clear()
        await admin_command(message, state)
        
    else:
        await message.answer("ℹ️ Используйте кнопки для управления ботом пользователя")

# Обработка документов для подключенного бота
@router.message(AdminStates.connected_bot_state, F.document)
async def handle_zip_file_for_connected_bot(message: Message, state: FSMContext):
    """Обработка ZIP файлов для подключенного бота"""
    admin_id = message.from_user.id
    
    if admin_id not in connected_bots:
        await state.clear()
        return
    
    target_user_id = connected_bots[admin_id]
    target_user_data = firebase_db.get_user(str(target_user_id))
    
    if not target_user_data or not target_user_data.get('hosting_plan'):
        await message.answer("❌ У пользователя нет активного хостинга")
        return
    
    document = message.document
    if not document.file_name or not document.file_name.endswith('.zip'):
        await message.answer("❌ Пожалуйста, загрузите файл в формате ZIP")
        return
    
    try:
        # Уведомляем о начале обработки
        processing_msg = await message.answer("🔄 Начинаю обработку ZIP архива...")
        
        # Скачиваем файл
        file = await message.bot.get_file(document.file_id)
        file_content = await message.bot.download_file(file.file_path)
        file_bytes = file_content.read()
        
        await processing_msg.edit_text("📦 Распаковываю архив...")
        
        # Извлекаем ZIP для целевого пользователя
        files = await file_processor.extract_zip(file_bytes, target_user_id)
        
        if not files:
            await processing_msg.edit_text("❌ Не удалось извлечь файлы из архива")
            return
        
        await processing_msg.edit_text("💾 Сохраняю файлы...")
        
        # Сохраняем файлы локально для целевого пользователя
        local_saved = await file_processor.save_files_locally(files, target_user_id)
        
        # Автоматически находим основной файл
        from handlers.files import get_correct_main_file_path
        main_file_path, main_file_name = get_correct_main_file_path(target_user_id)
        
        # Обновляем статус в Firebase для целевого пользователя
        updates = {
            'has_files': True,
            'files_count': local_saved
        }
        
        if main_file_name and main_file_name != "Python файлы не найдены":
            updates['main_file'] = main_file_name
        
        firebase_db.update_user(str(target_user_id), updates)
        
        success_text = f"""✅ Файлы успешно загружены для пользователя {target_user_id}!

📊 Статистика:
• Файлов в архиве: {len(files)}
• Сохранено локально: {local_saved}"""
        
        if main_file_name and main_file_name != "Python файлы не найдены":
            success_text += f"\n• Автоматически выбран основной файл: {main_file_name}"
        
        # Проверяем наличие requirements.txt
        if file_processor.check_requirements_file(target_user_id):
            requirements_content = file_processor.get_requirements_content(target_user_id)
            if requirements_content:
                lib_count = len([line for line in requirements_content.split('\n') if line.strip() and not line.strip().startswith('#')])
                success_text += f"\n\n📦 Обнаружен requirements.txt ({lib_count} библиотек)"
        
        success_text += "\n\nТеперь вы можете запустить скрипт пользователя!"
        
        await processing_msg.edit_text(success_text)
        
    except Exception as e:
        error_text = f"❌ Ошибка при обработке файла: {str(e)}"
        try:
            await processing_msg.edit_text(error_text)
        except:
            await message.answer(error_text)

# Остальной код админ-панели остается без изменений...
# [Здесь должен быть весь остальной код из предыдущей версии admin.py]

@router.message(F.text == "👑 Управление админами")
async def admin_management_handler(message: Message):
    """Управление администраторами"""
    user_id = message.from_user.id
    
    if not check_admin_access(user_id):
        await message.answer("❌ Недостаточно прав")
        return
    
    admins = firebase_db.get_all_admins()
    
    if not admins:
        await message.answer("❌ Администраторы не найдены")
        return
    
    admins_text = "👑 <b>Список администраторов:</b>\n\n"
    for admin_id, admin_data in admins.items():
        level = admin_data.get('admin_level', 0)
        level_text = ""
        if level == 3:
            level_text = "👑 Владелец"
        elif level == 2:
            level_text = "⚡ Админ"
        elif level == 1:
            level_text = "🛡️ Модератор"
        
        admins_text += f"🆔 ID: {admin_id}\n"
        admins_text += f"👤 Имя: {admin_data.get('first_name', 'Неизвестно')}\n"
        admins_text += f"📊 Уровень: {level_text}\n"
        admins_text += "─" * 30 + "\n"
    
    admins_text += "\n<b>Команды:</b>\n"
    admins_text += "<code>/set_admin ID_ПОЛЬЗОВАТЕЛЯ УРОВЕНЬ</code> - назначить админа\n"
    admins_text += "<code>/remove_admin ID_ПОЛЬЗОВАТЕЛЯ</code> - снять админа\n"
    admins_text += "\n<b>Уровни:</b>\n"
    admins_text += "3 - Владелец (все права)\n"
    admins_text += "2 - Админ (баланс, хостинг, пользователи)\n" 
    admins_text += "1 - Модератор (пользователи, промокоды)\n"
    
    await message.answer(admins_text, parse_mode="HTML")

@router.message(Command("set_admin"))
async def set_admin_handler(message: Message):
    """Назначить администратора"""
    user_id = message.from_user.id
    
    if not check_admin_access(user_id):
        await message.answer("❌ Недостаточно прав")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("❌ Использование: /set_admin <user_id> <level>")
            return
        
        target_user_id = parts[1]
        level = int(parts[2])
        
        if level not in [1, 2, 3]:
            await message.answer("❌ Уровень должен быть 1, 2 или 3")
            return
        
        target_user_data = firebase_db.get_user(target_user_id)
        if not target_user_data:
            await message.answer("❌ Пользователь не найден")
            return
        
        if firebase_db.set_admin(target_user_id, level):
            level_text = {1: "Модератор", 2: "Админ", 3: "Владелец"}[level]
            await message.answer(f"✅ Пользователь {target_user_id} назначен {level_text}")
        else:
            await message.answer("❌ Ошибка назначения админа")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("remove_admin"))
async def remove_admin_handler(message: Message):
    """Снять администратора"""
    user_id = message.from_user.id
    
    if not check_admin_access(user_id):
        await message.answer("❌ Недостаточно прав")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /remove_admin <user_id>")
            return
        
        target_user_id = parts[1]
        
        if target_user_id == str(ADMIN_ID):
            await message.answer("❌ Нельзя снять владельца")
            return
        
        if firebase_db.set_admin(target_user_id, 0):
            await message.answer(f"✅ Пользователь {target_user_id} снят с админки")
        else:
            await message.answer("❌ Ошибка снятия админа")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(F.text == "👥 Управление пользователями")
async def admin_users_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        await message.answer("❌ Недостаточно прав")
        return
    await state.clear()
    await message.answer("👥 Управление пользователями", reply_markup=get_admin_users_keyboard())

@router.message(F.text == "📊 Список пользователей")
async def users_list_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    users = firebase_db.get_all_users()
    if not users:
        await message.answer("❌ Пользователи не найдены")
        return
    
    users_text = "👥 Список пользователей:\n\n"
    for user_id, user_data in users.items():
        users_text += f"🆔 ID: {user_id}\n"
        users_text += f"👤 Имя: {user_data.get('first_name', 'Не указано')}\n"
        users_text += f"💰 Баланс: {user_data.get('balance', 0)}₽\n"
        users_text += f"🚀 Хостинг: {user_data.get('hosting_plan', 'Нет')}\n"
        users_text += f"📅 Регистрация: {user_data.get('created_at', 'Не указано')}\n"
        users_text += f"🔴 Статус: {'Забанен' if user_data.get('is_banned') else 'Активен'}\n"
        users_text += f"👑 Админ: {'Да' if user_data.get('is_admin') else 'Нет'}\n"
        users_text += "─" * 30 + "\n"
    
    if len(users_text) > 4000:
        parts = [users_text[i:i+4000] for i in range(0, len(users_text), 4000)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(users_text)

@router.message(F.text == "🔨 Бан/Разбан")
async def ban_management_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    await message.answer(
        "🔨 Бан/Разбан пользователя\n\n"
        "Для бана пользователя:\n"
        "<code>/ban ID_ПОЛЬЗОВАТЕЛЯ</code>\n\n"
        "Для разбана пользователя:\n"
        "<code>/unban ID_ПОЛЬЗОВАТЕЛЯ</code>\n\n"
        "Пример:\n"
        "<code>/ban 123456789</code>\n"
        "<code>/unban 123456789</code>",
        parse_mode="HTML"
    )

@router.message(Command("ban"))
async def ban_user_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /ban <user_id>")
            return
        
        user_id = parts[1]
        if firebase_db.ban_user(user_id):
            await message.answer(f"✅ Пользователь {user_id} забанен")
        else:
            await message.answer(f"❌ Ошибка при бане пользователя {user_id}")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("unban"))
async def unban_user_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /unban <user_id>")
            return
        
        user_id = parts[1]
        if firebase_db.unban_user(user_id):
            await message.answer(f"✅ Пользователь {user_id} разбанен")
        else:
            await message.answer(f"❌ Ошибка при разбане пользователя {user_id}")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(F.text == "🛑 Остановить бота")
async def stop_bot_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    await message.answer(
        "🛑 Остановка бота пользователя\n\n"
        "Для остановки бота пользователя:\n"
        "<code>/stop_bot ID_ПОЛЬЗОВАТЕЛЯ</code>\n\n"
        "Пример:\n"
        "<code>/stop_bot 123456789</code>",
        parse_mode="HTML"
    )

@router.message(Command("stop_bot"))
async def stop_user_bot_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /stop_bot <user_id>")
            return
        
        user_id = parts[1]
        await script_runner.stop_script(int(user_id))
        firebase_db.stop_user_script(user_id)
        
        await message.answer(f"✅ Бот пользователя {user_id} остановлен")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(F.text == "💰 Управление балансом")
async def admin_balance_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        await message.answer("❌ Недостаточно прав")
        return
    await state.clear()
    await message.answer("💰 Управление балансом", reply_markup=get_admin_balance_keyboard())

@router.message(F.text == "💸 Выдать баланс")
async def add_balance_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_user_id)
    await state.update_data(action="add_balance")
    await message.answer("Введите ID пользователя для выдачи баланса:", reply_markup=get_admin_back_keyboard())

@router.message(F.text == "➖ Списать баланс")
async def remove_balance_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_user_id)
    await state.update_data(action="remove_balance")
    await message.answer("Введите ID пользователя для списания баланса:", reply_markup=get_admin_back_keyboard())

@router.message(AdminStates.waiting_user_id)
async def process_user_id(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    user_id = message.text.strip()
    user_data = firebase_db.get_user(user_id)
    if not user_data:
        await message.answer("❌ Пользователь не найден")
        return
    
    await state.update_data(user_id=user_id)
    await state.set_state(AdminStates.waiting_balance_amount)
    
    data = await state.get_data()
    action_type = "выдачи" if data.get('action') == 'add_balance' else "списания"
    
    await message.answer(f"Введите сумму для {action_type} баланса пользователю {user_id}:")

@router.message(AdminStates.waiting_balance_amount)
async def process_balance_amount(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительным числом")
            return
        
        data = await state.get_data()
        user_id = data.get('user_id')
        action = data.get('action')
        
        if action == 'add_balance':
            new_balance = firebase_db.update_balance(user_id, amount)
            await message.answer(f"✅ Баланс пользователя {user_id} пополнен на {amount}₽\nНовый баланс: {new_balance}₽")
        else:
            new_balance = firebase_db.update_balance(user_id, -amount)
            await message.answer(f"✅ С пользователя {user_id} списано {amount}₽\nНовый баланс: {new_balance}₽")
        
        await state.clear()
        await message.answer("💰 Управление балансом", reply_markup=get_admin_balance_keyboard())
    
    except ValueError:
        await message.answer("❌ Введите корректное число")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(F.text == "🚀 Управление хостингом")
async def admin_hosting_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        await message.answer("❌ Недостаточно прав")
        return
    
    await state.clear()
    
    hosting_text = """🚀 Управление хостингом

Текущие тарифы:
• 7 дней - 60₽
• 14 дней - 100₽  
• 30 дней - 150₽

Выберите действие:"""
    
    await message.answer(hosting_text, reply_markup=get_admin_hosting_keyboard())

@router.message(F.text == "💳 Изменить цену")
async def change_price_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    await message.answer(
        "💳 Изменение цены хостинга\n\n"
        "Используйте команды:\n"
        "<code>/set_price_7days НОВАЯ_ЦЕНА</code>\n"
        "<code>/set_price_14days НОВАЯ_ЦЕНА</code>\n"
        "<code>/set_price_30days НОВАЯ_ЦЕНА</code>\n\n"
        "Пример:\n"
        "<code>/set_price_7days 70</code>",
        parse_mode="HTML"
    )

@router.message(Command("set_price_7days"))
async def set_price_7days_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /set_price_7days <цена>")
            return
        
        price = int(parts[1])
        if firebase_db.update_hosting_price("7days", price):
            await message.answer(f"✅ Цена тарифа 7 дней изменена на {price}₽")
        else:
            await message.answer("❌ Ошибка при изменении цены")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("set_price_14days"))
async def set_price_14days_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /set_price_14days <цена>")
            return
        
        price = int(parts[1])
        if firebase_db.update_hosting_price("14days", price):
            await message.answer(f"✅ Цена тарифа 14 дней изменена на {price}₽")
        else:
            await message.answer("❌ Ошибка при изменении цены")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("set_price_30days"))
async def set_price_30days_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /set_price_30days <цена>")
            return
        
        price = int(parts[1])
        if firebase_db.update_hosting_price("30days", price):
            await message.answer(f"✅ Цена тарифа 30 дней изменена на {price}₽")
        else:
            await message.answer("❌ Ошибка при изменении цены")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(F.text == "📅 Изменить длительность")
async def change_duration_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    await message.answer(
        "📅 Изменение длительности хостинга\n\n"
        "Используйте команды:\n"
        "<code>/set_duration_7days НОВАЯ_ДЛИТЕЛЬНОСТЬ</code>\n"
        "<code>/set_duration_14days НОВАЯ_ДЛИТЕЛЬНОСТЬ</code>\n"
        "<code>/set_duration_30days НОВАЯ_ДЛИТЕЛЬНОСТЬ</code>\n\n"
        "Пример:\n"
        "<code>/set_duration_7days 10</code>",
        parse_mode="HTML"
    )

@router.message(Command("set_duration_7days"))
async def set_duration_7days_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /set_duration_7days <дней>")
            return
        
        days = int(parts[1])
        if firebase_db.update_hosting_duration("7days", days):
            await message.answer(f"✅ Длительность тарифа 7 дней изменена на {days} дней")
        else:
            await message.answer("❌ Ошибка при изменении длительности")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("set_duration_14days"))
async def set_duration_14days_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /set_duration_14days <дней>")
            return
        
        days = int(parts[1])
        if firebase_db.update_hosting_duration("14days", days):
            await message.answer(f"✅ Длительность тарифа 14 дней изменена на {days} дней")
        else:
            await message.answer("❌ Ошибка при изменении длительности")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("set_duration_30days"))
async def set_duration_30days_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /set_duration_30days <дней>")
            return
        
        days = int(parts[1])
        if firebase_db.update_hosting_duration("30days", days):
            await message.answer(f"✅ Длительность тарифа 30 дней изменена на {days} дней")
        else:
            await message.answer("❌ Ошибка при изменении длительности")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(F.text == "🎫 Управление промокодами")
async def admin_promo_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        await message.answer("❌ Недостаточно прав")
        return
    
    await state.clear()
    await message.answer("🎫 Управление промокодами", reply_markup=get_admin_promo_keyboard())

@router.message(F.text == "➕ Создать промокод")
async def create_promo_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_promo_code)
    await message.answer("Введите код промокода:", reply_markup=get_admin_back_keyboard())

@router.message(AdminStates.waiting_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    promo_code = message.text.strip().upper()
    if len(promo_code) < 3:
        await message.answer("❌ Код промокода должен содержать минимум 3 символа")
        return
    
    await state.update_data(promo_code=promo_code)
    await state.set_state(AdminStates.waiting_promo_type)
    
    await message.answer("Выберите тип награды:", reply_markup=get_admin_back_keyboard())

@router.message(AdminStates.waiting_promo_type)
async def process_promo_type(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    promo_type = message.text.strip().lower()
    if promo_type not in ['balance', 'hosting']:
        await message.answer("❌ Выберите тип: 'balance' или 'hosting'")
        return
    
    await state.update_data(promo_type=promo_type)
    await state.set_state(AdminStates.waiting_promo_value)
    
    reward_type = "баланс" if promo_type == 'balance' else "хостинг"
    await message.answer(f"Введите значение награды ({reward_type}):")

@router.message(AdminStates.waiting_promo_value)
async def process_promo_value(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        value = int(message.text.strip())
        if value <= 0:
            await message.answer("❌ Значение должно быть положительным числом")
            return
        
        await state.update_data(promo_value=value)
        await state.set_state(AdminStates.waiting_promo_limit)
        
        await message.answer("Введите лимит использований (по умолчанию 1):")
    
    except ValueError:
        await message.answer("❌ Введите корректное число")

@router.message(AdminStates.waiting_promo_limit)
async def process_promo_limit(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        limit = int(message.text.strip()) if message.text.strip().isdigit() else 1
        if limit <= 0:
            await message.answer("❌ Лимит должен быть положительным числом")
            return
        
        data = await state.get_data()
        promo_code = data.get('promo_code')
        promo_type = data.get('promo_type')
        promo_value = data.get('promo_value')
        
        if firebase_db.create_promo_code(promo_code, promo_type, promo_value, limit):
            reward_text = f"{promo_value}₽" if promo_type == 'balance' else f"хостинг на {promo_value} дней"
            await message.answer(f"✅ Промокод создан!\n\n"
                               f"🎫 Код: {promo_code}\n"
                               f"🎁 Награда: {reward_text}\n"
                               f"📊 Лимит: {limit} использований")
        else:
            await message.answer("❌ Ошибка при создании промокода")
        
        await state.clear()
        await message.answer("🎫 Управление промокодами", reply_markup=get_admin_promo_keyboard())
    
    except ValueError:
        await message.answer("❌ Введите корректное число")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(F.text == "📋 Список промокодов")
async def list_promos_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    promos = firebase_db.get_promo_codes()
    if not promos:
        await message.answer("❌ Промокоды не найдены")
        return
    
    promos_text = "📋 Список промокодов:\n\n"
    for code, promo_data in promos.items():
        reward_type = "💰 Баланс" if promo_data.get('reward_type') == 'balance' else "🚀 Хостинг"
        reward_value = f"{promo_data.get('reward_value')}₽" if promo_data.get('reward_type') == 'balance' else f"{promo_data.get('reward_value')} дней"
        
        promos_text += f"🎫 Код: {code}\n"
        promos_text += f"🎁 Награда: {reward_type} - {reward_value}\n"
        promos_text += f"📊 Использовано: {promo_data.get('used_count', 0)}/{promo_data.get('uses_limit', 1)}\n"
        promos_text += f"🔧 Статус: {'🟢 Активен' if promo_data.get('is_active', True) else '🔴 Неактивен'}\n"
        promos_text += "─" * 30 + "\n"
    
    await message.answer(promos_text[:4000])

@router.message(F.text == "🗑️ Удалить промокод")
async def delete_promo_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    await message.answer(
        "🗑️ Удаление промокода\n\n"
        "Для удаления промокода:\n"
        "<code>/delete_promo КОД_ПРОМОКОДА</code>\n\n"
        "Пример:\n"
        "<code>/delete_promo SUMMER2024</code>",
        parse_mode="HTML"
    )

@router.message(Command("delete_promo"))
async def delete_promo_command(message: Message):
    if not check_admin_access(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /delete_promo <code>")
            return
        
        code = parts[1]
        if firebase_db.delete_promo_code(code):
            await message.answer(f"✅ Промокод {code} удален")
        else:
            await message.answer(f"❌ Ошибка при удалении промокода")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(F.text == "📈 Статистика")
async def stats_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        await message.answer("❌ Недостаточно прав")
        return
    
    users = firebase_db.get_all_users()
    total_users = len(users)
    total_balance = sum(user.get('balance', 0) for user in users.values())
    active_hosting = sum(1 for user in users.values() if user.get('hosting_plan'))
    banned_users = sum(1 for user in users.values() if user.get('is_banned'))
    admin_users = sum(1 for user in users.values() if user.get('is_admin'))
    
    from datetime import datetime, timedelta
    active_users_30_days = 0
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    for user_data in users.values():
        created_at = user_data.get('created_at')
        if created_at:
            try:
                user_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                if user_date >= thirty_days_ago:
                    active_users_30_days += 1
            except:
                pass
    
    stats_text = f"""📈 Статистика бота

👥 Пользователи:
• Всего пользователей: {total_users}
• Новых за 30 дней: {active_users_30_days}
• Активных хостингов: {active_hosting}
• Забаненных: {banned_users}
• Администраторов: {admin_users}

💰 Финансы:
• Общий баланс: {total_balance}₽
• Средний баланс: {total_balance/max(total_users, 1):.1f}₽

🚀 Хостинг:
• Тарифы: 7д/60₽, 14д/100₽, 30д/150₽"""

    await message.answer(stats_text)

@router.message(F.text == "🔄 Принудительная проверка")
async def force_check_handler(message: Message):
    if not check_admin_access(message.from_user.id):
        await message.answer("❌ Недостаточно прав")
        return
    
    from utils.hosting_manager import hosting_manager
    await hosting_manager.check_hosting_expiry()
    await message.answer("✅ Принудительная проверка хостингов выполнена")

@router.message(F.text == "🔙 Назад")
async def back_handler(message: Message, state: FSMContext):
    if not check_admin_access(message.from_user.id):
        return
    
    # Выходим из режима подключенного бота если был
    if message.from_user.id in connected_bots:
        del connected_bots[message.from_user.id]
    
    await state.clear()
    user_data = firebase_db.get_user(str(message.from_user.id))
    admin_level = user_data.get('admin_level', 0) if user_data else 0
    await message.answer("👨‍💻 Панель администратора", reply_markup=get_admin_keyboard(admin_level))

@router.message(F.text == "🔙 Главное меню")
async def back_to_main_handler(message: Message, state: FSMContext):
    # Выходим из режима подключенного бота если был
    if message.from_user.id in connected_bots:
        del connected_bots[message.from_user.id]
    
    await state.clear()
    user_data = firebase_db.get_user(str(message.from_user.id)) or {}
    await message.answer("Главное меню:", reply_markup=get_main_keyboard(user_data))