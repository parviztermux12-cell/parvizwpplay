from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import subprocess
import asyncio
import os
import json
from firebase_db import firebase_db
from keyboards import get_libraries_main_keyboard, get_libraries_back_keyboard, get_back_to_files_keyboard
from utils.script_runner import script_runner

router = Router()

class LibraryStates(StatesGroup):
    waiting_install = State()

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def get_user_folder(user_id: int) -> str:
    """Получить папку пользователя"""
    return f"user_files/{user_id}"

def get_libraries_file(user_id: int) -> str:
    """Получить файл с библиотеками"""
    user_folder = get_user_folder(user_id)
    os.makedirs(user_folder, exist_ok=True)
    return os.path.join(user_folder, "libraries.json")

def load_libraries(user_id: int) -> list:
    """Загрузить список библиотек"""
    lib_file = get_libraries_file(user_id)
    if os.path.exists(lib_file):
        try:
            with open(lib_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_libraries(user_id: int, libraries: list):
    """Сохранить список библиотек"""
    lib_file = get_libraries_file(user_id)
    with open(lib_file, 'w', encoding='utf-8') as f:
        json.dump(libraries, f, ensure_ascii=False, indent=2)

def add_library(user_id: int, library: str):
    """Добавить библиотеку"""
    libraries = load_libraries(user_id)
    if library not in libraries:
        libraries.append(library)
        save_libraries(user_id, libraries)

def remove_library(user_id: int, library: str):
    """Удалить библиотеку"""
    libraries = load_libraries(user_id)
    if library in libraries:
        libraries.remove(library)
        save_libraries(user_id, libraries)

def has_active_hosting(user_id: int) -> bool:
    """Проверить активный хостинг"""
    user_data = firebase_db.get_user(str(user_id))
    
    if not user_data:
        print(f"❌ Пользователь {user_id} не найден в базе")
        return False
    
    hosting_plan = user_data.get('hosting_plan')
    hosting_expiry = user_data.get('hosting_expiry')
    
    print(f"🔍 Проверка хостинга для {user_id}:")
    print(f"   Хостинг: {hosting_plan}")
    print(f"   Истекает: {hosting_expiry}")
    
    if not hosting_plan or not hosting_expiry:
        print(f"❌ Нет хостинга или даты истечения")
        return False
    
    # Проверяем дату истечения
    from datetime import datetime
    try:
        expiry_date = datetime.strptime(hosting_expiry, "%d.%m.%Y %H:%M")
        current_date = datetime.now()
        is_active = current_date <= expiry_date
        print(f"✅ Хостинг активен: {is_active}")
        return is_active
    except Exception as e:
        print(f"❌ Ошибка парсинга даты: {e}")
        try:
            expiry_date = datetime.strptime(hosting_expiry, "%d.%m.%Y")
            current_date = datetime.now()
            is_active = current_date <= expiry_date
            print(f"✅ Хостинг активен: {is_active}")
            return is_active
        except Exception as e2:
            print(f"❌ Ошибка парсинга даты 2: {e2}")
            return False

def has_requirements_file(user_id: int) -> bool:
    """Проверить наличие requirements.txt"""
    requirements_path = os.path.join(get_user_folder(user_id), "requirements.txt")
    return os.path.exists(requirements_path)

# ===== ГЛАВНОЕ МЕНЮ БИБЛИОТЕК =====

async def libraries_main_menu(callback: CallbackQuery, is_script_running=False):
    """Главное меню библиотек для вызова из других файлов"""
    user_id = callback.from_user.id
    
    if not has_active_hosting(user_id):
        await callback.answer("❌ У вас нет активного хостинга", show_alert=True)
        return
    
    libraries = load_libraries(user_id)
    
    text = "📚 <b>Управление библиотеками</b>\n\n"
    
    if is_script_running:
        text += "⚠️ <b>Скрипт запущен - установка и удаление библиотек заблокированы</b>\n\n"
    
    if libraries:
        text += "📦 <b>Установленные библиотеки:</b>\n"
        for lib in libraries:
            text += f"• {lib}\n"
        text += f"\n📊 Всего: {len(libraries)} библиотек\n\n"
    else:
        text += "📦 Установленные библиотеки отсутствуют\n\n"
    
    if has_requirements_file(user_id):
        text += "📁 <b>Обнаружен requirements.txt</b>\n\n"
    
    text += "💡 Выберите действие:"
    
    await callback.message.edit_text(
        text, 
        reply_markup=get_libraries_main_keyboard(has_requirements_file(user_id), is_script_running),
        parse_mode="HTML"
    )
    await callback.answer()

# ===== ОСНОВНЫЕ ОБРАБОТЧИКИ =====

@router.callback_query(F.data == "open_libraries")
async def open_libraries_handler(callback: CallbackQuery):
    """Открыть меню библиотек из файлов"""
    user_id = callback.from_user.id
    is_script_running = script_runner.is_script_running(user_id)
    await libraries_main_menu(callback, is_script_running)

@router.callback_query(F.data == "libraries_show")
async def show_libraries_handler(callback: CallbackQuery):
    """Показать установленные библиотеки"""
    user_id = callback.from_user.id
    
    if not has_active_hosting(user_id):
        await callback.answer("❌ Нет активного хостинга", show_alert=True)
        return
    
    libraries = load_libraries(user_id)
    
    if not libraries:
        await callback.message.edit_text(
            "📦 <b>Библиотеки не установлены</b>",
            reply_markup=get_libraries_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    text = "📦 <b>Установленные библиотеки:</b>\n\n"
    for i, lib in enumerate(libraries, 1):
        text += f"{i}. {lib}\n"
    
    text += f"\n📊 Всего: {len(libraries)} библиотек"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_libraries_back_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "libraries_install")
async def install_library_handler(callback: CallbackQuery, state: FSMContext):
    """Установка библиотеки - ввод названия"""
    user_id = callback.from_user.id
    
    if not has_active_hosting(user_id):
        await callback.answer("❌ Нет активного хостинга", show_alert=True)
        return
    
    # Проверяем, запущен ли скрипт
    if script_runner.is_script_running(user_id):
        await callback.answer("❌ Нельзя устанавливать библиотеки пока скрипт запущен", show_alert=True)
        return
    
    await state.set_state(LibraryStates.waiting_install)
    
    await callback.message.edit_text(
        "📥 <b>Установка библиотеки</b>\n\n"
        "Введите название библиотеки для установки:\n\n"
        "📝 <b>Примеры:</b>\n"
        "• requests\n"
        "• python-telegram-bot\n"
        "• beautifulsoup4\n\n"
        "❌ Для отмены нажмите 'Назад'",
        reply_markup=get_libraries_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(LibraryStates.waiting_install)
async def process_install_library(message: Message, state: FSMContext):
    """Обработка установки библиотеки"""
    user_id = message.from_user.id
    library_name = message.text.strip()
    
    if not has_active_hosting(user_id):
        await message.answer("❌ Нет активного хостинга")
        await state.clear()
        return
    
    # Проверяем, запущен ли скрипт
    if script_runner.is_script_running(user_id):
        await message.answer("❌ Нельзя устанавливать библиотеки пока скрипт запущен")
        await state.clear()
        return
    
    if not library_name:
        await message.answer("❌ Введите название библиотеки")
        return
    
    # Проверка безопасности
    dangerous = [';', '&', '|', '`', '$', '(', ')', '{', '}', '[', ']', '>', '<', 'sudo', 'rm']
    if any(char in library_name for char in dangerous):
        await message.answer("❌ Недопустимые символы в названии")
        return
    
    # Установка
    msg = await message.answer(f"🔄 Устанавливаю <b>{library_name}</b>...", parse_mode="HTML")
    
    try:
        process = await asyncio.create_subprocess_exec(
            'pip', 'install', library_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            add_library(user_id, library_name)
            await msg.edit_text(f"✅ Библиотека <b>{library_name}</b> установлена!", parse_mode="HTML")
        else:
            error = stderr.decode().strip()
            await msg.edit_text(f"❌ Ошибка установки:\n<code>{error}</code>", parse_mode="HTML")
            
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)}")
    
    await state.clear()

@router.callback_query(F.data == "libraries_install_requirements")
async def install_requirements_handler(callback: CallbackQuery):
    """Установка из requirements.txt"""
    user_id = callback.from_user.id
    
    if not has_active_hosting(user_id):
        await callback.answer("❌ Нет активного хостинга", show_alert=True)
        return
    
    # Проверяем, запущен ли скрипт
    if script_runner.is_script_running(user_id):
        await callback.answer("❌ Нельзя устанавливать библиотеки пока скрипт запущен", show_alert=True)
        return
    
    req_file = os.path.join(get_user_folder(user_id), "requirements.txt")
    
    if not os.path.exists(req_file):
        await callback.answer("❌ Файл requirements.txt не найден", show_alert=True)
        return
    
    await callback.message.edit_text("🔄 Устанавливаю библиотеки из requirements.txt...")
    
    try:
        process = await asyncio.create_subprocess_exec(
            'pip', 'install', '-r', req_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            # Добавляем библиотеки в список
            with open(req_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        lib_name = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                        if lib_name:
                            add_library(user_id, lib_name)
            
            await callback.message.edit_text(
                "✅ Библиотеки из requirements.txt установлены!",
                reply_markup=get_libraries_back_keyboard()
            )
        else:
            error = stderr.decode().strip()
            await callback.message.edit_text(
                f"❌ Ошибка установки:\n<code>{error}</code>",
                reply_markup=get_libraries_back_keyboard(),
                parse_mode="HTML"
            )
            
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_libraries_back_keyboard()
        )
    
    await callback.answer()

@router.callback_query(F.data == "libraries_uninstall")
async def uninstall_library_handler(callback: CallbackQuery):
    """Удаление библиотеки - выбор"""
    user_id = callback.from_user.id
    
    if not has_active_hosting(user_id):
        await callback.answer("❌ Нет активного хостинга", show_alert=True)
        return
    
    # Проверяем, запущен ли скрипт
    if script_runner.is_script_running(user_id):
        await callback.answer("❌ Нельзя удалять библиотеки пока скрипт запущен", show_alert=True)
        return
    
    libraries = load_libraries(user_id)
    
    if not libraries:
        await callback.message.edit_text(
            "❌ Нет установленных библиотек",
            reply_markup=get_libraries_back_keyboard()
        )
        return
    
    builder = InlineKeyboardBuilder()
    
    for lib in libraries:
        builder.button(text=f"🗑️ {lib}", callback_data=f"uninstall_{lib}")
    
    builder.button(text="🔙 Назад", callback_data="libraries_back")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "🗑️ <b>Выберите библиотеку для удаления:</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("uninstall_"))
async def process_uninstall_handler(callback: CallbackQuery):
    """Обработка удаления библиотеки"""
    user_id = callback.from_user.id
    library_name = callback.data.replace("uninstall_", "")
    
    if not has_active_hosting(user_id):
        await callback.answer("❌ Нет активного хостинга", show_alert=True)
        return
    
    # Проверяем, запущен ли скрипт
    if script_runner.is_script_running(user_id):
        await callback.answer("❌ Нельзя удалять библиотеки пока скрипт запущен", show_alert=True)
        return
    
    await callback.message.edit_text(f"🔄 Удаляю <b>{library_name}</b>...", parse_mode="HTML")
    
    try:
        process = await asyncio.create_subprocess_exec(
            'pip', 'uninstall', '-y', library_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            remove_library(user_id, library_name)
            await callback.message.edit_text(f"✅ Библиотека <b>{library_name}</b> удалена!", parse_mode="HTML")
        else:
            error = stderr.decode().strip()
            await callback.message.edit_text(f"❌ Ошибка удаления:\n<code>{error}</code>", parse_mode="HTML")
            
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
    
    # Возвращаем к списку библиотек
    libraries = load_libraries(user_id)
    if libraries:
        builder = InlineKeyboardBuilder()
        for lib in libraries:
            builder.button(text=f"🗑️ {lib}", callback_data=f"uninstall_{lib}")
        builder.button(text="🔙 Назад", callback_data="libraries_back")
        builder.adjust(1)
        
        await callback.message.answer(
            "🗑️ <b>Выберите библиотеку для удаления:</b>",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            "📦 Больше нет установленных библиотек",
            reply_markup=get_libraries_back_keyboard()
        )
    
    await callback.answer()

@router.callback_query(F.data == "libraries_help")
async def libraries_help_handler(callback: CallbackQuery):
    """Справка по библиотекам"""
    text = (
        "💡 <b>Справка по библиотекам</b>\n\n"
        "📚 <b>Библиотеки</b> - это дополнительные пакеты Python,\n"
        "которые расширяют функциональность вашего бота.\n\n"
        "🔧 <b>Доступные действия:</b>\n"
        "• 📦 Показать библиотеки - список установленных\n"
        "• 📥 Установить библиотеку - установить новую\n" 
        "• 📁 Установить из requirements.txt - массовая установка\n"
        "• 🗑️ Удалить библиотеку - удалить установленную\n\n"
        "🚫 <b>Ограничения:</b>\n"
        "• Установка и удаление библиотек заблокированы\n"
        "  когда скрипт запущен\n\n"
        "💡 <b>Совет:</b> Используйте requirements.txt для удобной\n"
        "установки всех зависимостей вашего проекта."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_libraries_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.in_(["libraries_locked"]))
async def locked_libraries_callback(callback: CallbackQuery):
    """Обработчик заблокированных действий библиотек"""
    await callback.answer("❌ Это действие заблокировано пока скрипт запущен", show_alert=True)

@router.callback_query(F.data == "libraries_back")
async def libraries_back_handler(callback: CallbackQuery, state: FSMContext):
    """Назад в меню библиотек"""
    await state.clear()
    user_id = callback.from_user.id
    is_script_running = script_runner.is_script_running(user_id)
    await libraries_main_menu(callback, is_script_running)

@router.callback_query(F.data == "back_to_files")
async def back_to_files_handler(callback: CallbackQuery, state: FSMContext):
    """Назад к файлам"""
    from handlers.files import files_handler
    await state.clear()
    await files_handler(callback.message)
    await callback.answer()

# Обработчик для очистки состояния при командах
@router.message(LibraryStates.waiting_install)
async def clear_library_state_on_commands(message: Message, state: FSMContext):
    """Очищаем состояние при командах"""
    if message.text and message.text.startswith('/'):
        await state.clear()
        return
    await message.answer("❌ Введите название библиотеки или нажмите 'Назад'")