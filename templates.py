from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from firebase_db import firebase_db
from keyboards import (
    get_templates_keyboard, 
    get_template_settings_keyboard,
    get_template_config_keyboard,
    get_main_keyboard
)
from config import BOT_TEMPLATES
import os
import json
import shutil
from datetime import datetime

router = Router()

class TemplateStates(StatesGroup):
    waiting_bot_token = State()
    waiting_admin_ids = State()
    waiting_template_install = State()
    waiting_welcome_message = State()
    waiting_subscription_message = State()
    waiting_channels = State()
    waiting_payment_methods = State()
    waiting_currency = State()
    waiting_ref_reward = State()

def get_template_config_file(user_id: int, template_type: str) -> str:
    user_folder = f"user_files/{user_id}"
    os.makedirs(user_folder, exist_ok=True)
    return os.path.join(user_folder, f"{template_type}_config.json")

def load_template_config(user_id: int, template_type: str) -> dict:
    config_file = get_template_config_file(user_id, template_type)
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_template_config(user_id: int, template_type: str, config: dict):
    config_file = get_template_config_file(user_id, template_type)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def copy_template_files(template_type: str, user_id: int, config: dict):
    template_folder = f"templates/{template_type}"
    user_folder = f"user_files/{user_id}"
    
    if not os.path.exists(template_folder):
        return False
    
    if os.path.exists(user_folder):
        shutil.rmtree(user_folder)
    os.makedirs(user_folder, exist_ok=True)
    
    try:
        for item in os.listdir(template_folder):
            source_path = os.path.join(template_folder, item)
            dest_path = os.path.join(user_folder, item)
            
            if os.path.isfile(source_path):
                shutil.copy2(source_path, dest_path)
        
        # Сохраняем конфиг в основной файл конфигурации
        config_file_path = os.path.join(user_folder, "config.json")
        with open(config_file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка копирования файлов шаблона: {e}")
        return False

def has_active_hosting(user_data) -> bool:
    """Проверить активный хостинг"""
    hosting_plan = user_data.get('hosting_plan')
    hosting_expiry = user_data.get('hosting_expiry')
    
    if not hosting_plan or not hosting_expiry:
        return False
    
    try:
        expiry_date = datetime.strptime(hosting_expiry, "%d.%m.%Y %H:%M")
        return datetime.now() <= expiry_date
    except:
        try:
            expiry_date = datetime.strptime(hosting_expiry, "%d.%m.%Y")
            return datetime.now() <= expiry_date
        except:
            return False

# ===== ОСНОВНЫЕ ОБРАБОТЧИКИ =====

@router.message(F.text == "📋 Шаблоны")
async def templates_handler(message: Message):
    await message.answer(
        "📋 <b>Готовые шаблоны ботов</b>\n\n"
        "Выберите шаблон для быстрого создания бота:",
        reply_markup=get_templates_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.text == "⚙️ Конфигурация")
async def configuration_handler(message: Message):
    """Обработчик кнопки конфигурации из главного меню"""
    user_id = message.from_user.id
    user_data = firebase_db.get_user(str(user_id)) or {}
    
    # Определяем тип установленного шаблона
    template_type = user_data.get('template_type')
    if not template_type:
        await message.answer("❌ Шаблон не установлен или тип шаблона не определен")
        return
    
    config = load_template_config(user_id, template_type)
    
    text = f"""<b>⚙️ Конфигурация шаблона</b>

📋 <b>Текущая конфигурация:</b>"""
    
    if config:
        for key, value in config.items():
            if key == 'bot_token' and value:
                text += f"\n• 🤖 Токен бота: {'✅ Установлен' if value else '❌ Не установлен'}"
            elif key == 'admin_ids' and value:
                text += f"\n• 👑 Админы: {len(value)} пользователей"
            elif key == 'welcome_message' and value:
                text += f"\n• 👋 Приветствие: {'✅ Установлено' if value else '❌ Не установлено'}"
            elif key == 'subscription_message' and value:
                text += f"\n• 💬 Сообщение подписки: {'✅ Установлено' if value else '❌ Не установлено'}"
            elif key == 'channels' and value:
                text += f"\n• 📢 Каналы: {len(value)} каналов"
            elif key == 'payment_methods' and value:
                text += f"\n• 💳 Способы пополнения: {value}"
            elif key == 'currency' and value:
                text += f"\n• 💰 Валюта: {value}"
            elif key == 'ref_reward' and value:
                text += f"\n• 🎁 Реф награда: {value}%"
    else:
        text += "\n❌ Конфигурация не настроена"
    
    text += "\n\n⚙️ Выберите параметр для настройки:"
    
    await message.answer(
        text,
        reply_markup=get_template_config_keyboard(template_type),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "back_to_templates")
async def back_to_templates_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 <b>Готовые шаблоны ботов</b>\n\n"
        "Выберите шаблон для быстрого создания бота:",
        reply_markup=get_templates_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "template_shop_bot")
async def template_shop_bot_callback(callback: CallbackQuery):
    """Обработчик для шаблона магазина"""
    await show_template_details(callback, "shop_bot")

@router.callback_query(F.data == "template_subscription_bot")
async def template_subscription_bot_callback(callback: CallbackQuery):
    """Обработчик для шаблона подписок"""
    await show_template_details(callback, "subscription_bot")

async def show_template_details(callback: CallbackQuery, template_type: str):
    """Показать детали шаблона"""
    print(f"🎯 ПОКАЗ ДЕТАЛЕЙ ШАБЛОНА: {template_type}")
    
    if template_type not in BOT_TEMPLATES:
        await callback.answer(f"❌ Шаблон '{template_type}' не найден. Доступные: {list(BOT_TEMPLATES.keys())}", show_alert=True)
        return
    
    template = BOT_TEMPLATES[template_type]
    user_id = callback.from_user.id
    
    user_data = firebase_db.get_user(str(user_id)) or {}
    balance = user_data.get('balance', 0)
    
    text = f"""<b>{template['name']}</b>
💵 Цена: {template['price']}₽

📝 <b>Описание:</b>
{template['description']}

✨ <b>Возможности:</b>
"""
    
    for feature in template['features']:
        text += f"• {feature}\n"
    
    text += f"\n💳 Ваш баланс: {balance}₽"
    
    if balance < template['price']:
        text += f"\n❌ Недостаточно средств. Нужно еще {template['price'] - balance}₽"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_template_settings_keyboard(template_type),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("template_settings_"))
async def template_settings_callback(callback: CallbackQuery):
    template_type = callback.data.replace("template_settings_", "")
    
    print(f"🎯 НАСТРОЙКИ ШАБЛОНА: {template_type}")
    print(f"🎯 CALLBACK DATA: {callback.data}")
    
    if template_type not in BOT_TEMPLATES:
        await callback.answer(f"❌ Шаблон '{template_type}' не найден. Доступные: {list(BOT_TEMPLATES.keys())}", show_alert=True)
        return
    
    template = BOT_TEMPLATES[template_type]
    user_id = callback.from_user.id
    
    config = load_template_config(user_id, template_type)
    
    text = f"""<b>⚙️ Настройки {template['name']}</b>

📋 <b>Текущая конфигурация:</b>"""
    
    if config:
        for key, value in config.items():
            if key == 'bot_token' and value:
                text += f"\n• 🤖 Токен бота: {'✅ Установлен' if value else '❌ Не установлен'}"
            elif key == 'admin_ids' and value:
                text += f"\n• 👑 Админы: {len(value)} пользователей"
            elif key == 'welcome_message' and value:
                text += f"\n• 👋 Приветствие: {'✅ Установлено' if value else '❌ Не установлено'}"
            elif key == 'subscription_message' and value:
                text += f"\n• 💬 Сообщение подписки: {'✅ Установлено' if value else '❌ Не установлено'}"
            elif key == 'channels' and value:
                text += f"\n• 📢 Каналы: {len(value)} каналов"
            elif key == 'payment_methods' and value:
                text += f"\n• 💳 Способы пополнения: {value}"
            elif key == 'currency' and value:
                text += f"\n• 💰 Валюта: {value}"
            elif key == 'ref_reward' and value:
                text += f"\n• 🎁 Реф награда: {value}%"
    else:
        text += "\n❌ Конфигурация не настроена"
    
    text += "\n\n⚙️ Настройте параметры перед установкой:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_template_config_keyboard(template_type),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("template_config_"))
async def template_config_callback(callback: CallbackQuery):
    template_type = callback.data.replace("template_config_", "")
    
    print(f"🎯 КОНФИГУРАЦИЯ ШАБЛОНА: {template_type}")
    
    if template_type not in BOT_TEMPLATES:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚙️ <b>Конфигурация шаблона</b>\n\n"
        "Выберите параметр для настройки:",
        reply_markup=get_template_config_keyboard(template_type),
        parse_mode="HTML"
    )
    await callback.answer()

# ===== ОБРАБОТЧИКИ КОНФИГУРАЦИИ =====

@router.callback_query(F.data.startswith("config_bot_token_"))
async def config_bot_token_callback(callback: CallbackQuery, state: FSMContext):
    template_type = callback.data.replace("config_bot_token_", "")
    
    print(f"🎯 НАСТРОЙКА ТОКЕНА ДЛЯ: {template_type}")
    
    await state.set_state(TemplateStates.waiting_bot_token)
    await state.update_data(template_type=template_type)
    
    await callback.message.edit_text(
        "🤖 <b>Настройка токена бота</b>\n\n"
        "Отправьте токен вашего бота от @BotFather:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(TemplateStates.waiting_bot_token)
async def process_bot_token(message: Message, state: FSMContext):
    bot_token = message.text.strip()
    data = await state.get_data()
    template_type = data.get('template_type')
    
    if not bot_token or ':' not in bot_token:
        await message.answer("❌ Неверный формат токена. Попробуйте еще раз.")
        return
    
    user_id = message.from_user.id
    config = load_template_config(user_id, template_type)
    config['bot_token'] = bot_token
    save_template_config(user_id, template_type, config)
    
    await message.answer("✅ Токен бота сохранен!")
    await state.clear()

@router.callback_query(F.data.startswith("config_admin_ids_"))
async def config_admin_ids_callback(callback: CallbackQuery, state: FSMContext):
    template_type = callback.data.replace("config_admin_ids_", "")
    
    print(f"🎯 НАСТРОЙКА АДМИНОВ ДЛЯ: {template_type}")
    
    await state.set_state(TemplateStates.waiting_admin_ids)
    await state.update_data(template_type=template_type)
    
    await callback.message.edit_text(
        "👑 <b>Настройка администраторов</b>\n\n"
        "Отправьте ID администраторов через запятую:\n\n"
        "💡 <b>Пример:</b>\n"
        "<code>123456789, 987654321</code>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(TemplateStates.waiting_admin_ids)
async def process_admin_ids(message: Message, state: FSMContext):
    admin_ids_text = message.text.strip()
    data = await state.get_data()
    template_type = data.get('template_type')
    
    try:
        admin_ids = [int(id.strip()) for id in admin_ids_text.split(',')]
        
        user_id = message.from_user.id
        config = load_template_config(user_id, template_type)
        config['admin_ids'] = admin_ids
        save_template_config(user_id, template_type, config)
        
        await message.answer(f"✅ ID администраторов сохранены! ({len(admin_ids)} пользователей)")
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат ID. Используйте числа через запятую.")

@router.callback_query(F.data.startswith("config_welcome_"))
async def config_welcome_callback(callback: CallbackQuery, state: FSMContext):
    template_type = callback.data.replace("config_welcome_", "")
    
    await state.set_state(TemplateStates.waiting_welcome_message)
    await state.update_data(template_type=template_type)
    
    await callback.message.edit_text(
        "👋 <b>Настройка приветственного сообщения</b>\n\n"
        "Отправьте текст приветственного сообщения:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(TemplateStates.waiting_welcome_message)
async def process_welcome_message(message: Message, state: FSMContext):
    welcome_text = message.text.strip()
    data = await state.get_data()
    template_type = data.get('template_type')
    
    user_id = message.from_user.id
    config = load_template_config(user_id, template_type)
    config['welcome_message'] = welcome_text
    save_template_config(user_id, template_type, config)
    
    await message.answer("✅ Приветственное сообщение сохранено!")
    await state.clear()

@router.callback_query(F.data.startswith("config_subscription_"))
async def config_subscription_callback(callback: CallbackQuery, state: FSMContext):
    template_type = callback.data.replace("config_subscription_", "")
    
    await state.set_state(TemplateStates.waiting_subscription_message)
    await state.update_data(template_type=template_type)
    
    await callback.message.edit_text(
        "💬 <b>Настройка сообщения о подписке</b>\n\n"
        "Отправьте текст сообщения о подписке:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(TemplateStates.waiting_subscription_message)
async def process_subscription_message(message: Message, state: FSMContext):
    subscription_text = message.text.strip()
    data = await state.get_data()
    template_type = data.get('template_type')
    
    user_id = message.from_user.id
    config = load_template_config(user_id, template_type)
    config['subscription_message'] = subscription_text
    save_template_config(user_id, template_type, config)
    
    await message.answer("✅ Сообщение о подписке сохранено!")
    await state.clear()

@router.callback_query(F.data.startswith("config_channels_"))
async def config_channels_callback(callback: CallbackQuery, state: FSMContext):
    template_type = callback.data.replace("config_channels_", "")
    
    await state.set_state(TemplateStates.waiting_channels)
    await state.update_data(template_type=template_type)
    
    await callback.message.edit_text(
        "📢 <b>Настройка каналов для подписки</b>\n\n"
        "Отправьте ссылки на каналы через запятую:\n\n"
        "💡 <b>Пример:</b>\n"
        "<code>@channel1, @channel2, https://t.me/channel3</code>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(TemplateStates.waiting_channels)
async def process_channels(message: Message, state: FSMContext):
    channels_text = message.text.strip()
    data = await state.get_data()
    template_type = data.get('template_type')
    
    channels = [channel.strip() for channel in channels_text.split(',')]
    
    user_id = message.from_user.id
    config = load_template_config(user_id, template_type)
    config['channels'] = channels
    save_template_config(user_id, template_type, config)
    
    await message.answer(f"✅ Каналы сохранены! ({len(channels)} каналов)")
    await state.clear()

@router.callback_query(F.data.startswith("config_payment_"))
async def config_payment_callback(callback: CallbackQuery, state: FSMContext):
    template_type = callback.data.replace("config_payment_", "")
    
    await state.set_state(TemplateStates.waiting_payment_methods)
    await state.update_data(template_type=template_type)
    
    await callback.message.edit_text(
        "💳 <b>Настройка способов пополнения</b>\n\n"
        "Отправьте способы пополнения через запятую:\n\n"
        "💡 <b>Пример:</b>\n"
        "<code>QIWI, ЮMoney, Банковская карта, Криптовалюта</code>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(TemplateStates.waiting_payment_methods)
async def process_payment_methods(message: Message, state: FSMContext):
    payment_text = message.text.strip()
    data = await state.get_data()
    template_type = data.get('template_type')
    
    user_id = message.from_user.id
    config = load_template_config(user_id, template_type)
    config['payment_methods'] = payment_text
    save_template_config(user_id, template_type, config)
    
    await message.answer("✅ Способы пополнения сохранены!")
    await state.clear()

@router.callback_query(F.data.startswith("config_currency_"))
async def config_currency_callback(callback: CallbackQuery, state: FSMContext):
    template_type = callback.data.replace("config_currency_", "")
    
    await state.set_state(TemplateStates.waiting_currency)
    await state.update_data(template_type=template_type)
    
    await callback.message.edit_text(
        "💰 <b>Настройка валюты</b>\n\n"
        "Отправьте валюту для бота:\n\n"
        "💡 <b>Пример:</b>\n"
        "<code>RUB</code> или <code>USD</code> или <code>EUR</code>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(TemplateStates.waiting_currency)
async def process_currency(message: Message, state: FSMContext):
    currency = message.text.strip().upper()
    data = await state.get_data()
    template_type = data.get('template_type')
    
    user_id = message.from_user.id
    config = load_template_config(user_id, template_type)
    config['currency'] = currency
    save_template_config(user_id, template_type, config)
    
    await message.answer(f"✅ Валюта '{currency}' сохранена!")
    await state.clear()

@router.callback_query(F.data.startswith("config_ref_reward_"))
async def config_ref_reward_callback(callback: CallbackQuery, state: FSMContext):
    template_type = callback.data.replace("config_ref_reward_", "")
    
    await state.set_state(TemplateStates.waiting_ref_reward)
    await state.update_data(template_type=template_type)
    
    await callback.message.edit_text(
        "🎁 <b>Настройка реферальной награды</b>\n\n"
        "Отправьте процент реферальной награды:\n\n"
        "💡 <b>Пример:</b>\n"
        "<code>10</code> (для 10%)",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(TemplateStates.waiting_ref_reward)
async def process_ref_reward(message: Message, state: FSMContext):
    try:
        ref_reward = int(message.text.strip())
        data = await state.get_data()
        template_type = data.get('template_type')
        
        user_id = message.from_user.id
        config = load_template_config(user_id, template_type)
        config['ref_reward'] = ref_reward
        save_template_config(user_id, template_type, config)
        
        await message.answer(f"✅ Реферальная награда {ref_reward}% сохранена!")
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите корректное число (например: 10)")

# ===== УСТАНОВКА ШАБЛОНА =====

@router.callback_query(F.data.startswith("template_install_"))
async def template_install_callback(callback: CallbackQuery, state: FSMContext):
    template_type = callback.data.replace("template_install_", "")
    
    print(f"🎯 УСТАНОВКА ШАБЛОНА: {template_type}")
    
    if template_type not in BOT_TEMPLATES:
        await callback.answer(f"❌ Шаблон '{template_type}' не найден. Доступные: {list(BOT_TEMPLATES.keys())}", show_alert=True)
        return
    
    template = BOT_TEMPLATES[template_type]
    user_id = callback.from_user.id
    
    user_data = firebase_db.get_user(str(user_id)) or {}
    balance = user_data.get('balance', 0)
    
    # Проверяем наличие активного хостинга
    if not has_active_hosting(user_data):
        await callback.answer(
            "❌ Вы не можете установить шаблон так как у вас нет активного хостинга", 
            show_alert=True
        )
        return
    
    if balance < template['price']:
        await callback.answer(f"❌ Недостаточно средств. Нужно еще {template['price'] - balance}₽", show_alert=True)
        return
    
    # Проверяем наличие токена бота
    config = load_template_config(user_id, template_type)
    if not config.get('bot_token'):
        # Если токена нет, запрашиваем его
        await state.set_state(TemplateStates.waiting_template_install)
        await state.update_data(template_type=template_type)
        
        await callback.message.edit_text(
            "🤖 <b>Установка шаблона</b>\n\n"
            "Для установки шаблона требуется токен бота.\n\n"
            "Отправьте токен вашего бота от @BotFather:",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Если токен есть, устанавливаем шаблон
    await install_template(callback, template_type, user_id, config)

@router.message(TemplateStates.waiting_template_install)
async def process_template_install_with_token(message: Message, state: FSMContext):
    """Обработка установки шаблона с вводом токена"""
    bot_token = message.text.strip()
    data = await state.get_data()
    template_type = data.get('template_type')
    
    if not bot_token or ':' not in bot_token:
        await message.answer("❌ Неверный формат токена. Попробуйте еще раз.")
        return
    
    user_id = message.from_user.id
    
    # Проверяем наличие активного хостинга перед установкой
    user_data = firebase_db.get_user(str(user_id)) or {}
    if not has_active_hosting(user_data):
        await message.answer(
            "❌ <b>Установка отменена!</b>\n\n"
            "Вы не можете установить данный шаблон так как у вас нет активного хостинга.\n\n"
            "💰 <b>Деньги возвращены на ваш счет</b>\n"
            "💳 Для установки шаблона необходимо приобрести хостинг",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    # Сохраняем токен в конфиг
    config = load_template_config(user_id, template_type)
    config['bot_token'] = bot_token
    save_template_config(user_id, template_type, config)
    
    # Устанавливаем шаблон
    template = BOT_TEMPLATES[template_type]
    new_balance = firebase_db.update_balance(str(user_id), -template['price'])
    
    success = copy_template_files(template_type, user_id, config)
    
    if not success:
        firebase_db.update_balance(str(user_id), template['price'])
        await message.answer("❌ Ошибка при копировании файлов шаблона")
        await state.clear()
        return
    
    # Подсчитываем файлы
    user_folder = f"user_files/{user_id}"
    file_count = len([f for f in os.listdir(user_folder) if os.path.isfile(os.path.join(user_folder, f))])
    
    # Обновляем данные пользователя
    firebase_db.update_user(str(user_id), {
        'has_files': True,
        'files_count': file_count,
        'main_file': 'main.py',
        'balance': new_balance,
        'is_template': True,  # Помечаем что установлен шаблон
        'template_type': template_type  # Сохраняем тип шаблона
    })
    
    success_text = f"""✅ <b>Шаблон установлен!</b>

📦 {template['name']}
💵 Стоимость: {template['price']}₽
💳 Новый баланс: {new_balance}₽

🚀 <b>Шаблон готов к использованию!</b>
📁 Файлов установлено: {file_count}"""

    await message.answer(success_text, parse_mode="HTML")
    await state.clear()

async def install_template(callback: CallbackQuery, template_type: str, user_id: int, config: dict):
    """Установка шаблона (вспомогательная функция)"""
    template = BOT_TEMPLATES[template_type]
    
    # Проверяем наличие активного хостинга перед установкой
    user_data = firebase_db.get_user(str(user_id)) or {}
    if not has_active_hosting(user_data):
        await callback.answer(
            "❌ Вы не можете установить шаблон так как у вас нет активного хостинга", 
            show_alert=True
        )
        return
    
    # Детальная отладка
    template_folder = f"templates/{template_type}"
    print(f"🔍 Проверка шаблона '{template_type}':")
    print(f"📁 Путь: {template_folder}")
    print(f"✅ Папка существует: {os.path.exists(template_folder)}")
    
    if os.path.exists(template_folder):
        files = os.listdir(template_folder)
        print(f"📄 Файлы в папке: {files}")
    
    if not os.path.exists(template_folder):
        await callback.answer(f"❌ Папка шаблона не найдена по пути: {template_folder}", show_alert=True)
        return
    
    new_balance = firebase_db.update_balance(str(user_id), -template['price'])
    
    success = copy_template_files(template_type, user_id, config)
    
    if not success:
        firebase_db.update_balance(str(user_id), template['price'])
        await callback.answer("❌ Ошибка при копировании файлов шаблона", show_alert=True)
        return
    
    # Подсчитываем файлы
    user_folder = f"user_files/{user_id}"
    file_count = len([f for f in os.listdir(user_folder) if os.path.isfile(os.path.join(user_folder, f))])
    
    # Обновляем данные пользователя
    firebase_db.update_user(str(user_id), {
        'has_files': True,
        'files_count': file_count,
        'main_file': 'main.py',
        'balance': new_balance,
        'is_template': True,  # Помечаем что установлен шаблон
        'template_type': template_type  # Сохраняем тип шаблона
    })
    
    success_text = f"""✅ <b>Шаблон установлен!</b>

📦 {template['name']}
💵 Стоимость: {template['price']}₽
💳 Новый баланс: {new_balance}₽

🚀 <b>Шаблон готов к использованию!</b>
📁 Файлов установлено: {file_count}"""

    await callback.message.edit_text(success_text, parse_mode="HTML")
    await callback.answer("✅ Шаблон успешно установлен!")

@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery):
    user_data = firebase_db.get_user(str(callback.from_user.id)) or {}
    await callback.message.edit_text("Главное меню:")
    await callback.message.answer("Выберите действие:", reply_markup=get_main_keyboard(user_data))
    await callback.answer()