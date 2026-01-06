from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from firebase_db import firebase_db
from keyboards import get_files_keyboard, get_main_keyboard, get_back_to_files_keyboard
from utils.file_processing import file_processor
from utils.script_runner import script_runner
import os
import base64
import aiofiles
import asyncio
import shutil

router = Router()

def get_correct_main_file_path(user_id: int) -> tuple:
    """Найти корректный путь к основному файлу"""
    user_folder = f"user_files/{user_id}"
    
    if not os.path.exists(user_folder):
        return None, "Папка не существует"
    
    # Получаем данные из базы
    user_data = firebase_db.get_user(str(user_id))
    if not user_data:
        return None, "Пользователь не найден в базе"
    
    main_file_from_db = user_data.get('main_file', 'main.py')
    
    # Сначала пробуем найти файл по пути из базы
    potential_path = os.path.join(user_folder, main_file_from_db)
    
    if os.path.exists(potential_path):
        return potential_path, main_file_from_db
    
    # Если не нашли, ищем любой main.py в проекте
    for root, dirs, files in os.walk(user_folder):
        for file in files:
            if file == 'main.py':
                found_path = os.path.join(root, file)
                rel_path = os.path.relpath(found_path, user_folder)
                return found_path, rel_path
    
    # Если main.py не нашли, ищем любой Python файл
    for root, dirs, files in os.walk(user_folder):
        for file in files:
            if file.endswith('.py'):
                found_path = os.path.join(root, file)
                rel_path = os.path.relpath(found_path, user_folder)
                return found_path, rel_path
    
    return None, "Python файлы не найдены"

def get_available_python_files(user_id: int) -> list:
    """Получить список всех Python файлов"""
    user_folder = f"user_files/{user_id}"
    python_files = []
    
    if not os.path.exists(user_folder):
        return []
    
    for root, dirs, files in os.walk(user_folder):
        for file in files:
            if file.endswith('.py'):
                rel_path = os.path.relpath(os.path.join(root, file), user_folder)
                python_files.append(rel_path)
    
    return sorted(python_files)

@router.message(F.text == "📁 Файлы")
async def files_handler(message: Message):
    user_id = message.from_user.id
    is_script_running = script_runner.is_script_running(user_id)
    user_data = firebase_db.get_user(str(user_id)) or {}
    is_template = user_data.get('is_template', False)
    
    warning_text = ""
    if is_script_running:
        warning_text += "\n\n⚠️ <b>Скрипт запущен - некоторые действия заблокированы</b>"
    if is_template:
        warning_text += "\n\n🚫 <b>Установлен шаблон - скачивание файлов заблокировано</b>"
    
    await message.answer(
        "Выбери пункт для управления файлами:" + warning_text,
        reply_markup=get_files_keyboard(is_script_running, is_template),
        parse_mode="HTML"
    )

# Обработчик для кнопки библиотек
@router.callback_query(F.data == "open_libraries")
async def open_libraries_callback(callback: CallbackQuery):
    """Открыть меню библиотек из файлов"""
    from handlers.libraries import libraries_main_menu
    user_id = callback.from_user.id
    is_script_running = script_runner.is_script_running(user_id)
    await libraries_main_menu(callback, is_script_running)

@router.callback_query(F.data == "back_to_files")
async def back_to_files_callback(callback: CallbackQuery):
    """Возврат к меню файлов"""
    user_id = callback.from_user.id
    is_script_running = script_runner.is_script_running(user_id)
    user_data = firebase_db.get_user(str(user_id)) or {}
    is_template = user_data.get('is_template', False)
    
    warning_text = ""
    if is_script_running:
        warning_text += "\n\n⚠️ <b>Скрипт запущен - некоторые действия заблокированы</b>"
    if is_template:
        warning_text += "\n\n🚫 <b>Установлен шаблон - скачивание файлов заблокировано</b>"
    
    await callback.message.edit_text(
        "Выбери пункт для управления файлами:" + warning_text,
        reply_markup=get_files_keyboard(is_script_running, is_template),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "show_files")
async def show_files_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Показываем файлы из локального хранилища
    file_list = file_processor.get_file_list_from_local(user_id)
    
    # Проверяем наличие requirements.txt
    if file_processor.check_requirements_file(user_id):
        requirements_content = file_processor.get_requirements_content(user_id)
        if requirements_content:
            lib_count = len([line for line in requirements_content.split('\n') if line.strip() and not line.strip().startswith('#')])
            file_list += f"\n\n📦 Обнаружен requirements.txt ({lib_count} библиотек)"
    
    await callback.message.edit_text(file_list, reply_markup=get_back_to_files_keyboard())

@router.callback_query(F.data == "delete_files")
async def delete_files_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Проверяем, запущен ли скрипт
    if script_runner.is_script_running(user_id):
        await callback.answer("❌ Нельзя удалять файлы пока скрипт запущен", show_alert=True)
        return
    
    # Удаляем локальные файлы
    user_folder = f"user_files/{user_id}"
    if os.path.exists(user_folder):
        shutil.rmtree(user_folder)
    
    # Обновляем статус в Firebase
    firebase_db.update_user(str(user_id), {
        'has_files': False,
        'files_count': 0,
        'is_template': False,  # Сбрасываем флаг шаблона
        'template_type': None  # Сбрасываем тип шаблона
    })
    
    await callback.message.edit_text("✅ Все файлы удалены", reply_markup=get_back_to_files_keyboard())

@router.callback_query(F.data == "download_files")
async def download_files_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Проверяем, запущен ли скрипт
    if script_runner.is_script_running(user_id):
        await callback.answer("❌ Нельзя скачивать файлы пока скрипт запущен", show_alert=True)
        return
    
    # Проверяем, установлен ли шаблон
    user_data = firebase_db.get_user(str(user_id)) or {}
    if user_data.get('is_template', False):
        await callback.answer(
            "❌ Скачать файлы невозможно так как у вас установлен шаблон готового бота и администратор запретил их скачивание", 
            show_alert=True
        )
        return
    
    # Проверяем есть ли локальные файлы
    if not file_processor.has_any_files(user_id):
        await callback.answer("❌ Файлы не найдены", show_alert=True)
        return
    
    try:
        # Создаем ZIP архив
        import zipfile
        zip_filename = f"user_{user_id}_files.zip"
        user_folder = f"user_files/{user_id}"
        
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for root, dirs, filenames in os.walk(user_folder):
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    arcname = os.path.relpath(filepath, user_folder)
                    zipf.write(filepath, arcname)
        
        # Отправляем ZIP файл
        document = FSInputFile(zip_filename)
        await callback.message.answer_document(document, caption="📁 Ваши файлы")
        
        # Очищаем временные файлы
        os.remove(zip_filename)
        await callback.answer("✅ Файлы отправлены")
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data.in_(["files_locked", "download_locked", "libraries_locked"]))
async def locked_actions_callback(callback: CallbackQuery):
    """Обработчик заблокированных действий"""
    user_id = callback.from_user.id
    user_data = firebase_db.get_user(str(user_id)) or {}
    
    if callback.data == "download_locked":
        if user_data.get('is_template', False):
            await callback.answer(
                "❌ Скачать файлы невозможно так как у вас установлен шаблон готового бота и администратор запретил их скачивание", 
                show_alert=True
            )
        else:
            await callback.answer("❌ Это действие заблокировано пока скрипт запущен", show_alert=True)
    else:
        await callback.answer("❌ Это действие заблокировано пока скрипт запущен", show_alert=True)

@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery):
    user_data = firebase_db.get_user(str(callback.from_user.id)) or {}
    await callback.message.edit_text("Главное меню:")
    await callback.message.answer("Выберите действие:", reply_markup=get_main_keyboard(user_data))
    await callback.answer()

@router.message(F.document)
async def handle_zip_file(message: Message):
    user_id = message.from_user.id
    
    # Проверяем, запущен ли скрипт
    if script_runner.is_script_running(user_id):
        await message.answer("❌ Нельзя загружать файлы пока скрипт запущен")
        return
    
    user_data = firebase_db.get_user(str(user_id))
    
    if not user_data or not user_data.get('hosting_plan'):
        await message.answer("❌ У вас нет активного хостинга")
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
        
        # Извлекаем ZIP
        files = await file_processor.extract_zip(file_bytes, user_id)
        
        if not files:
            await processing_msg.edit_text("❌ Не удалось извлечь файлы из архива")
            return
        
        await processing_msg.edit_text("💾 Сохраняю файлы...")
        
        # Сохраняем файлы локально
        local_saved = await file_processor.save_files_locally(files, user_id)
        
        # Автоматически находим основной файл
        main_file_path, main_file_name = get_correct_main_file_path(user_id)
        
        # Обновляем статус в Firebase
        updates = {
            'has_files': True,
            'files_count': local_saved,
            'is_template': False,  # Сбрасываем флаг шаблона при загрузке ZIP
            'template_type': None  # Сбрасываем тип шаблона
        }
        
        if main_file_name and main_file_name != "Python файлы не найдены":
            updates['main_file'] = main_file_name
        
        firebase_db.update_user(str(user_id), updates)
        
        success_text = f"""✅ Файлы успешно загружены!

📊 Статистика:
• Файлов в архиве: {len(files)}
• Сохранено локально: {local_saved}"""
        
        if main_file_name and main_file_name != "Python файлы не найдены":
            success_text += f"\n• Автоматически выбран основной файл: {main_file_name}"
        
        # Проверяем наличие requirements.txt
        if file_processor.check_requirements_file(user_id):
            requirements_content = file_processor.get_requirements_content(user_id)
            if requirements_content:
                lib_count = len([line for line in requirements_content.split('\n') if line.strip() and not line.strip().startswith('#')])
                success_text += f"\n\n📦 Обнаружен requirements.txt ({lib_count} библиотек)"
        
        success_text += "\n\nТеперь вы можете запустить свой скрипт!"
        
        await processing_msg.edit_text(success_text)
        
    except Exception as e:
        error_text = f"❌ Ошибка при обработке файла: {str(e)}"
        try:
            await processing_msg.edit_text(error_text)
        except:
            await message.answer(error_text)

@router.message(F.text == "📋 Логи")
async def logs_handler(message: Message):
    user_id = message.from_user.id
    user_data = firebase_db.get_user(str(user_id))
    
    if not user_data or not user_data.get('hosting_plan'):
        await message.answer("❌ У вас нет активного хостинга")
        return
    
    # Получаем все логи
    logs = await script_runner.get_logs(user_id)
    
    if not logs:
        await message.answer("📋 Логи не найдены (скрипт еще не запускался или не вывел данные)")
        return
    
    # Сохраняем логи во временный файл для отправки
    log_file = f"logs/user_{user_id}/current_logs.txt"
    async with aiofiles.open(log_file, 'w', encoding='utf-8') as f:
        await f.write(logs)
    
    try:
        document = FSInputFile(log_file)
        await message.answer_document(document, caption="📋 Полные логи выполнения скрипта")
    except Exception as e:
        await message.answer(f"❌ Ошибка при чтении логов: {str(e)}")

@router.message(F.text == "❌ Ошибки")
async def errors_handler(message: Message):
    user_id = message.from_user.id
    user_data = firebase_db.get_user(str(user_id))
    
    if not user_data or not user_data.get('hosting_plan'):
        await message.answer("❌ У вас нет активного хостинга")
        return
    
    # Получаем только ошибки
    errors = await script_runner.get_errors(user_id)
    
    if not errors:
        await message.answer("✅ Ошибок не обнаружено")
        return
    
    # Сохраняем ошибки во временный файл для отправки
    error_file = f"logs/user_{user_id}/current_errors.txt"
    async with aiofiles.open(error_file, 'w', encoding='utf-8') as f:
        await f.write("=== ОШИБКИ ВЫПОЛНЕНИЯ СКРИПТА ===\n\n")
        await f.write(errors)
    
    try:
        document = FSInputFile(error_file)
        await message.answer_document(document, caption="❌ Ошибки выполнения скрипта")
    except Exception as e:
        await message.answer(f"❌ Ошибка при чтении ошибок: {str(e)}")

@router.message(F.text == "⚙️ Основной файл")
async def main_file_handler(message: Message):
    user_id = message.from_user.id
    
    # Проверяем, запущен ли скрипт
    if script_runner.is_script_running(user_id):
        await message.answer("❌ Нельзя изменять основной файл пока скрипт запущен")
        return
    
    # Получаем все Python файлы
    python_files = get_available_python_files(user_id)
    
    if not python_files:
        await message.answer("❌ В ваших файлах нет Python скриптов (.py)")
        return
    
    file_list = "📁 Выберите основной файл (отправьте полный путь):\n\n"
    
    for i, filepath in enumerate(python_files, 1):
        file_list += f"{i}. {filepath}\n"
    
    file_list += f"\n📊 Всего Python файлов: {len(python_files)}"
    file_list += "\n\n📝 Чтобы выбрать файл, отправьте его полный путь"
    
    await message.answer(file_list)

@router.message(Command("debug_files"))
async def debug_files_handler(message: Message):
    user_id = message.from_user.id
    user_folder = f"user_files/{user_id}"
    
    if not os.path.exists(user_folder):
        await message.answer("❌ Папка не существует")
        return
    
    # Показываем реальную структуру файлов
    file_list = "📁 РЕАЛЬНАЯ СТРУКТУРА ФАЙЛОВ:\n\n"
    
    for root, dirs, files in os.walk(user_folder):
        level = root.replace(user_folder, '').count(os.sep)
        indent = '  ' * level
        file_list += f"{indent}📁 {os.path.basename(root)}/\n"
        
        subindent = '  ' * (level + 1)
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, user_folder)
            file_list += f"{subindent}📄 {file} (относительный путь: {rel_path})\n"
    
    # Показываем что в базе данных
    user_data = firebase_db.get_user(str(user_id))
    main_file = user_data.get('main_file', 'не установлен') if user_data else 'не установлен'
    has_files = user_data.get('has_files', False) if user_data else False
    hosting_plan = user_data.get('hosting_plan', 'нет') if user_data else 'нет'
    is_template = user_data.get('is_template', False) if user_data else False
    template_type = user_data.get('template_type', 'нет') if user_data else 'нет'
    is_script_running = script_runner.is_script_running(user_id)
    
    file_list += f"\n📋 В БАЗЕ ДАННЫХ:\n"
    file_list += f"Основной файл: {main_file}\n"
    file_list += f"Есть файлы: {'✅ Да' if has_files else '❌ Нет'}\n"
    file_list += f"Хостинг: {hosting_plan}\n"
    file_list += f"Шаблон установлен: {'✅ Да' if is_template else '❌ Нет'}\n"
    file_list += f"Тип шаблона: {template_type}\n"
    file_list += f"Скрипт запущен: {'✅ Да' if is_script_running else '❌ Нет'}\n"
    
    await message.answer(f"<code>{file_list}</code>", parse_mode="HTML")