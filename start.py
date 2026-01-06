from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from firebase_db import firebase_db
from keyboards import get_main_keyboard
from config import ADMIN_ID

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    try:
        # Create user in database
        is_new_user = firebase_db.create_user(user_id, first_name, username)
        
        # Check if user is admin
        if user_id == ADMIN_ID:
            firebase_db.update_user(user_id, {'is_admin': True})
        
        if is_new_user:
            welcome_text = f"""👋 Добро пожаловать в FlixHost хостинг для python, {first_name}!

<blockquote><b>Версия Бота: 1.0.0 [BETA]</b></blockquote>
<blockquote><b>Владелец бота: @ttmgudd</b></blockquote>

<b>Используйте кнопки ниже для навигации:</b>"""
        else:
            welcome_text = f"""👋 С возвращением в FlixHost, {first_name}!

<blockquote><b>Версия Бота: 1.0.0 [BETA]</b></blockquote>

<b>Используйте кнопки ниже для навигации:</b>"""
        
        # Получаем актуальные данные пользователя для клавиатуры
        user_data = firebase_db.get_user(user_id) or {}
        await message.answer(welcome_text, reply_markup=get_main_keyboard(user_data))
        
    except Exception as e:
        print(f"❌ Ошибка в команде /start: {e}")
        await message.answer("❌ Произошла ошибка при запуске бота. Попробуйте позже.")

@router.message(F.text == "🔙 Главное меню")
async def back_to_main(message: Message):
    try:
        user_data = firebase_db.get_user(message.from_user.id) or {}
        await message.answer("Главное меню:", reply_markup=get_main_keyboard(user_data))
    except Exception as e:
        print(f"❌ Ошибка в главном меню: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(Command("update_keyboard"))
async def update_keyboard_command(message: Message):
    """Команда для принудительного обновления клавиатуры"""
    user_id = message.from_user.id
    user_data = firebase_db.get_user(user_id) or {}
    
    await message.answer("🔄 Клавиатура обновлена", reply_markup=get_main_keyboard(user_data))