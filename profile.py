from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from firebase_db import firebase_db
from keyboards import get_profile_keyboard, get_python_version_keyboard, get_main_keyboard

router = Router()

@router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
    user_id = message.from_user.id
    user_data = firebase_db.get_user(user_id)
    
    if not user_data:
        await message.answer("Пользователь не найден")
        return
    
    # Форматируем дату списания
    hosting_expiry = user_data.get('hosting_expiry', 'Не установлено')
    if hosting_expiry and hosting_expiry != 'Не установлено':
        try:
            # Преобразуем в красивый формат
            from datetime import datetime
            expiry_date = datetime.strptime(hosting_expiry, "%d.%m.%Y %H:%M")
            hosting_expiry = expiry_date.strftime("%d.%m.%Y в %H:%M")
        except:
            pass
    
    profile_text = f"""👤 Профиль

Имя: {user_data.get('first_name', 'Не указано')}
ID: {user_id}
Баланс: {user_data.get('balance', 0)}₽
Хостинг: {user_data.get('hosting_plan', 'Не активирован')} | OC: Debian
Списание за хостинг: {hosting_expiry}
Имя основного файла: {user_data.get('main_file', 'main.py')}
Статус скрипта: {user_data.get('script_status', 'stopped')}
Версия Python: {user_data.get('python_version', '3.9')}

Характеристики сервера:
OC: Debian"""

    await message.answer(profile_text, reply_markup=get_profile_keyboard())

@router.callback_query(F.data == "change_python")
async def change_python_callback(callback: CallbackQuery):
    await callback.message.edit_text("Выберите версию Python:", reply_markup=get_python_version_keyboard())

@router.callback_query(F.data.startswith("python_"))
async def set_python_version_callback(callback: CallbackQuery):
    version = callback.data.replace("python_", "")
    user_id = callback.from_user.id
    
    firebase_db.update_user(user_id, {'python_version': version})
    
    await callback.message.edit_text(f"✅ Версия Python изменена на {version}")
    await callback.answer()