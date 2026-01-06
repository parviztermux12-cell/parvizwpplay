from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from firebase_db import firebase_db
from keyboards import get_hosting_plans_keyboard, get_buy_hosting_keyboard, get_main_keyboard, get_replenish_keyboard
from config import HOSTING_PLANS
from datetime import datetime, timedelta
import os
import psutil
from utils.script_runner import script_runner
from utils.file_processing import file_processor

router = Router()

@router.message(F.text == "🛒 Купить Хостинг")
async def buy_hosting_handler(message: Message):
    user_id = message.from_user.id
    user_data = firebase_db.get_user(user_id) or {}
    
    await message.answer("Выберите тариф хостинга:", reply_markup=get_hosting_plans_keyboard())

@router.callback_query(F.data.startswith("hosting_"))
async def hosting_details_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    plan_key = callback.data.replace("hosting_", "")
    
    if plan_key not in HOSTING_PLANS:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    plan = HOSTING_PLANS[plan_key]
    user_data = firebase_db.get_user(user_id) or {}
    balance = user_data.get('balance', 0)
    
    text = f"""👨‍💻 {plan['name']} | OC: {plan['os']}
Цена: {plan['price']}₽ / {plan['duration_days']} дней

Характеристики:
💾 Файлы: {plan['storage']}
🧠 ОЗУ: {plan['ram']}
🐍 Python: {', '.join(plan['python_versions'])}

Ваш баланс: {balance}₽"""
    
    if balance < plan['price']:
        text += f"\n\n❌ Недостаточно средств. Нужно еще {plan['price'] - balance}₽"
    
    await callback.message.edit_text(text, reply_markup=get_buy_hosting_keyboard(plan_key))

@router.callback_query(F.data.startswith("buy_"))
async def buy_hosting_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    plan_key = callback.data.replace("buy_", "")
    
    if plan_key not in HOSTING_PLANS:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    plan = HOSTING_PLANS[plan_key]
    user_data = firebase_db.get_user(user_id) or {}
    balance = user_data.get('balance', 0)
    
    if balance < plan['price']:
        await callback.answer(f"❌ Недостаточно средств. Нужно еще {plan['price'] - balance}₽", show_alert=True)
        return
    
    new_balance = firebase_db.update_balance(user_id, -plan['price'])
    expiry_date = (datetime.now() + timedelta(days=plan['duration_days'])).strftime("%d.%m.%Y %H:%M")
    
    updates = {
        'hosting_plan': plan['name'],
        'hosting_expiry': expiry_date,
        'balance': new_balance
    }
    firebase_db.update_user(user_id, updates)
    
    await callback.message.edit_text(
        f"✅ Хостинг успешно активирован!\n\n"
        f"📦 Тариф: {plan['name']}\n"
        f"💰 Стоимость: {plan['price']}₽\n"
        f"⏰ Активен до: {expiry_date}\n"
        f"💳 Новый баланс: {new_balance}₽\n\n"
        f"Теперь вы можете загружать свои скрипты и управлять ими"
    )
    await callback.message.answer("Выберите действие:", reply_markup=get_main_keyboard(updates))

@router.callback_query(F.data == "back_to_hosting")
async def back_to_hosting_callback(callback: CallbackQuery):
    await callback.message.edit_text("Выберите тариф хостинга:", reply_markup=get_hosting_plans_keyboard())

@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery):
    user_data = firebase_db.get_user(callback.from_user.id) or {}
    await callback.message.edit_text("Главное меню:")
    await callback.message.answer("Выберите действие:", reply_markup=get_main_keyboard(user_data))

def get_simple_main_file_path(user_id: int):
    user_folder = f"user_files/{user_id}"
    
    print(f"🔍 Поиск файла для пользователя {user_id}")
    print(f"📁 Папка: {user_folder}")
    
    if not os.path.exists(user_folder):
        print("❌ Папка не существует")
        return None, "Папка не существует"
    
    user_data = firebase_db.get_user(user_id)
    if not user_data:
        return None, "Пользователь не найден"
    
    main_file_name = user_data.get('main_file', 'main.py')
    print(f"📄 Основной файл из базы: '{main_file_name}'")
    
    path1 = os.path.join(user_folder, main_file_name)
    print(f"📍 Путь 1: {path1}")
    print(f"✅ Существует: {os.path.exists(path1)}")
    
    if os.path.exists(path1):
        print(f"🎯 Используем путь 1: {path1}")
        return path1, main_file_name
    
    path2 = os.path.join(user_folder, 'main.py')
    print(f"📍 Путь 2: {path2}")
    print(f"✅ Существует: {os.path.exists(path2)}")
    
    if os.path.exists(path2):
        print(f"🎯 Используем путь 2: {path2}")
        return path2, 'main.py'
    
    print("🔍 Ищем любой .py файл...")
    for root, dirs, files in os.walk(user_folder):
        for file in files:
            if file.endswith('.py'):
                found_path = os.path.join(root, file)
                rel_path = os.path.relpath(found_path, user_folder)
                print(f"🎯 Найден файл: {found_path}")
                print(f"📝 Относительный путь: {rel_path}")
                return found_path, rel_path
    
    print("❌ Python файлы не найдены")
    return None, "Python файлы не найдены"

@router.message(F.text == "🚀 Запустить")
async def start_script_handler(message: Message):
    user_id = message.from_user.id
    user_data = firebase_db.get_user(user_id)
    
    if not user_data or not user_data.get('hosting_plan'):
        await message.answer("❌ У вас нет активного хостинга")
        return
    
    # Проверяем наличие requirements.txt
    if file_processor.check_requirements_file(user_id):
        requirements_content = file_processor.get_requirements_content(user_id)
        if requirements_content:
            lib_count = len([line for line in requirements_content.split('\n') if line.strip() and not line.strip().startswith('#')])
            await message.answer(f"📦 Обнаружен requirements.txt ({lib_count} библиотек)\n💡 Рекомендуется установить библиотеки перед запуском")
    
    main_file_path, main_file_name = get_simple_main_file_path(user_id)
    
    if not main_file_path:
        await message.answer(f"❌ Не удалось найти файл для запуска: {main_file_name}")
        return
    
    if not os.path.exists(main_file_path):
        await message.answer(f"❌ Файл не существует: {main_file_path}")
        return
    
    absolute_path = os.path.abspath(main_file_path)
    print(f"📍 Абсолютный путь: {absolute_path}")
    print(f"✅ Абсолютный путь существует: {os.path.exists(absolute_path)}")
    
    if script_runner.is_script_running(user_id):
        await message.answer("⚠️ Скрипт уже запущен")
        return
    
    python_version = user_data.get('python_version', '3.9')
    starting_msg = await message.answer(f"🔄 Запускаю скрипт...\n\nФайл: {main_file_name}\nPython: {python_version}")
    
    print(f"🚀 ЗАПУСКАЕМ СКРИПТ:")
    print(f"📄 Файл: {absolute_path}")
    print(f"📁 Директория: {os.path.dirname(absolute_path)}")
    print(f"✅ Существует: {os.path.exists(absolute_path)}")
    
    success, result = await script_runner.start_script(user_id, absolute_path, python_version)
    
    if success:
        firebase_db.update_user(user_id, {'script_status': 'running'})
        
        success_text = f"""✅ Скрипт запущен!

📁 Файл: {main_file_name}
🐍 Python: {python_version}

💡Скрипт может запускаться более 2 минут (зависит от тяжести файлов)

📊 Статус: выполняется
💡 Логи доступны в меню "📋 Логи\""""
        
        await starting_msg.edit_text(success_text)
    else:
        error_text = f"❌ Ошибка запуска: {result}"
        print(error_text)
        await starting_msg.edit_text(error_text)

@router.message(F.text == "⏹️ Стоп")
async def stop_script_handler(message: Message):
    user_id = message.from_user.id
    
    if not script_runner.is_script_running(user_id):
        await message.answer("ℹ️ Скрипт не запущен")
        return
    
    stopping_msg = await message.answer("🔄 Останавливаю скрипт...")
    success = await script_runner.stop_script(user_id)
    
    if success:
        firebase_db.update_user(user_id, {'script_status': 'stopped'})
        await stopping_msg.edit_text("✅ Скрипт остановлен")
    else:
        await stopping_msg.edit_text("❌ Не удалось остановить скрипт")

@router.message(F.text == "📊 Ресурсы")
async def resources_handler(message: Message):
    user_id = message.from_user.id
    user_data = firebase_db.get_user(user_id)
    
    if not user_data or not user_data.get('hosting_plan'):
        await message.answer("❌ У вас нет активного хостинга")
        return
    
    user_folder = f"user_files/{user_id}"
    total_size = 0
    if os.path.exists(user_folder):
        for root, dirs, files in os.walk(user_folder):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
    
    size_mb = total_size / (1024 * 1024)
    
    script_status = "остановлен"
    if script_runner.is_script_running(user_id):
        script_status = "запущен"
    
    resources = script_runner.get_resource_usage(user_id)
    
    resources_text = f"""📊 Ресурсы:

🖥️ CPU: {resources['cpu']}
💾 ОЗУ: {resources['ram_used']} / {resources['ram_total']}
📁 Файлы: {size_mb:.2f} MB / 2000 MB
🚀 Скрипт: {script_status}"""

    await message.answer(resources_text)

@router.message(F.text == "📋 Логи")
async def logs_handler(message: Message):
    user_id = message.from_user.id
    user_data = firebase_db.get_user(user_id)
    
    if not user_data or not user_data.get('hosting_plan'):
        await message.answer("❌ У вас нет активного хостинга")
        return
    
    # Проверяем локальные логи
    log_file = f"logs/user_{user_id}/script.log"
    error_file = f"logs/user_{user_id}/error.log"
    
    has_logs = os.path.exists(log_file) and os.path.getsize(log_file) > 0
    has_errors = os.path.exists(error_file) and os.path.getsize(error_file) > 0
    
    if not has_logs and not has_errors:
        await message.answer("📋 Логи не найдены (скрипт еще не запускался или не вывел данные)")
        return
    
    # Отправляем логи
    if has_logs:
        try:
            document = FSInputFile(log_file)
            await message.answer_document(document, caption="📋 Логи выполнения скрипта")
        except Exception as e:
            await message.answer(f"❌ Ошибка при чтении логов: {str(e)}")
    
    # Отправляем ошибки если есть
    if has_errors:
        try:
            document = FSInputFile(error_file)
            await message.answer_document(document, caption="❌ Ошибки выполнения скрипта")
        except Exception as e:
            await message.answer(f"❌ Ошибка при чтении ошибок: {str(e)}")