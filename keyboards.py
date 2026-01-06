from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from config import HOSTING_PLANS

def get_main_keyboard(user_data):
    builder = ReplyKeyboardBuilder()
    
    builder.add(KeyboardButton(text="👤 Профиль"))
    
    hosting_plan = user_data.get('hosting_plan')
    hosting_expiry = user_data.get('hosting_expiry')
    
    has_active_hosting = False
    if hosting_plan and hosting_expiry:
        from datetime import datetime
        try:
            expiry_date = datetime.strptime(hosting_expiry, "%d.%m.%Y %H:%M")
            if datetime.now() <= expiry_date:
                has_active_hosting = True
        except:
            try:
                expiry_date = datetime.strptime(hosting_expiry, "%d.%m.%Y")
                if datetime.now() <= expiry_date:
                    has_active_hosting = True
            except:
                has_active_hosting = False
    
    # Проверяем, установлен ли шаблон
    is_template_installed = user_data.get('is_template', False)
    
    if has_active_hosting:
        builder.add(KeyboardButton(text="🚀 Запустить"))
        builder.add(KeyboardButton(text="⏹️ Стоп"))
        builder.add(KeyboardButton(text="📊 Ресурсы"))
        builder.add(KeyboardButton(text="📋 Логи"))
        builder.add(KeyboardButton(text="❌ Ошибки"))
        builder.add(KeyboardButton(text="📁 Файлы"))
        builder.add(KeyboardButton(text="⚙️ Основной файл"))
        
        # Добавляем кнопку конфигурации только если установлен шаблон
        if is_template_installed:
            builder.add(KeyboardButton(text="⚙️ Конфигурация"))
    else:
        builder.add(KeyboardButton(text="🛒 Купить Хостинг"))
    
    # Добавляем кнопку шаблонов в самый низ
    builder.add(KeyboardButton(text="📋 Шаблоны"))
    
    if has_active_hosting:
        if is_template_installed:
            builder.adjust(1, 2, 2, 2, 2, 1, 1, 1)  # С кнопкой конфигурации
        else:
            builder.adjust(1, 2, 2, 2, 2, 1, 1)  # Без кнопки конфигурации
    else:
        builder.adjust(1, 1, 1)  # Профиль, Купить хостинг, Шаблоны
    
    return builder.as_markup(resize_keyboard=True)

def get_replenish_keyboard():
    """Клавиатура для пополнения баланса"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="💳 Пополнить баланс", 
        callback_data="replenish_balance"
    ))
    return builder.as_markup()

def get_blocked_keyboard():
    """Клавиатура для заблокированного хостинга"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="💳 Пополнить баланс", 
        callback_data="replenish_balance"
    ))
    builder.add(InlineKeyboardButton(
        text="📥 Скачать скрипт",
        callback_data="download_files"
    ))
    builder.adjust(1)
    return builder.as_markup()

def get_hosting_plans_keyboard():
    """Клавиатура с выбором тарифов хостинга"""
    builder = InlineKeyboardBuilder()
    
    for plan_key, plan_data in HOSTING_PLANS.items():
        builder.add(InlineKeyboardButton(
            text=f"{plan_data['name']} | {plan_data['price']}₽", 
            callback_data=f"hosting_{plan_key}"
        ))
    
    builder.add(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="back_to_main"
    ))
    
    builder.adjust(1)
    return builder.as_markup()

def get_buy_hosting_keyboard(plan_key):
    """Клавиатура для покупки конкретного тарифа"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🛒 Купить", 
        callback_data=f"buy_{plan_key}"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 Назад", 
        callback_data="back_to_hosting"
    ))
    return builder.as_markup()

def get_profile_keyboard():
    """Клавиатура для профиля"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔄 Изменить версию Python", 
        callback_data="change_python"
    ))
    builder.add(InlineKeyboardButton(
        text="💳 Пополнить баланс", 
        callback_data="replenish_balance"
    ))
    builder.add(InlineKeyboardButton(
        text="🎫 Активировать промокод", 
        callback_data="activate_promo"
    ))
    builder.adjust(1)
    return builder.as_markup()

def get_python_version_keyboard():
    """Клавиатура для выбора версии Python"""
    builder = InlineKeyboardBuilder()
    versions = ["3.8", "3.9", "3.10", "3.11"]
    for version in versions:
        builder.add(InlineKeyboardButton(text=f"Python {version}", callback_data=f"python_{version}"))
    builder.adjust(2)
    return builder.as_markup()

def get_files_keyboard(is_script_running=False, is_template=False):
    """Клавиатура для управления файлами"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📁 Показать файлы", callback_data="show_files"))
    
    # Блокируем удаление если скрипт запущен
    if not is_script_running:
        builder.add(InlineKeyboardButton(text="🗑️ Удалить файлы", callback_data="delete_files"))
    else:
        builder.add(InlineKeyboardButton(text="🚫 Удалить файлы (скрипт запущен)", callback_data="files_locked"))
    
    # Блокируем скачивание если скрипт запущен ИЛИ установлен шаблон
    if not is_script_running and not is_template:
        builder.add(InlineKeyboardButton(text="📥 Скачать", callback_data="download_files"))
    elif is_template:
        builder.add(InlineKeyboardButton(text="🚫 Скачать (шаблон установлен)", callback_data="download_locked"))
    else:
        builder.add(InlineKeyboardButton(text="🚫 Скачать (скрипт запущен)", callback_data="download_locked"))
    
    builder.add(InlineKeyboardButton(text="📚 Библиотеки", callback_data="open_libraries"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

# Админские клавиатуры
def get_admin_keyboard(admin_level=1):
    """Главная клавиатура админ-панели с учетом уровня доступа"""
    builder = ReplyKeyboardBuilder()
    
    builder.add(KeyboardButton(text="👥 Управление пользователями"))
    builder.add(KeyboardButton(text="💰 Управление балансом"))
    
    if admin_level >= 2:
        builder.add(KeyboardButton(text="🚀 Управление хостингом"))
    
    builder.add(KeyboardButton(text="🎫 Управление промокодами"))
    builder.add(KeyboardButton(text="📈 Статистика"))
    
    if admin_level >= 3:
        builder.add(KeyboardButton(text="👑 Управление админами"))
        builder.add(KeyboardButton(text="🤖 Подключиться к боту"))
    
    builder.add(KeyboardButton(text="🔄 Принудительная проверка"))
    builder.add(KeyboardButton(text="🔙 Главное меню"))
    
    if admin_level >= 3:
        builder.adjust(2, 2, 2, 2, 1)
    else:
        builder.adjust(2, 2, 2, 1)
    
    return builder.as_markup(resize_keyboard=True)

def get_admin_users_keyboard():
    """Клавиатура для управления пользователями"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📊 Список пользователей"))
    builder.add(KeyboardButton(text="🔨 Бан/Разбан"))
    builder.add(KeyboardButton(text="🛑 Остановить бота"))
    builder.add(KeyboardButton(text="🔙 Назад"))
    builder.adjust(1, 2, 1)
    return builder.as_markup(resize_keyboard=True)

def get_admin_balance_keyboard():
    """Клавиатура для управления балансом"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💸 Выдать баланс"))
    builder.add(KeyboardButton(text="➖ Списать баланс"))
    builder.add(KeyboardButton(text="🔙 Назад"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def get_admin_hosting_keyboard():
    """Клавиатура для управления хостингом"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💳 Изменить цену"))
    builder.add(KeyboardButton(text="📅 Изменить длительность"))
    builder.add(KeyboardButton(text="🔙 Назад"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def get_admin_promo_keyboard():
    """Клавиатура для управления промокодами"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="➕ Создать промокод"))
    builder.add(KeyboardButton(text="📋 Список промокодов"))
    builder.add(KeyboardButton(text="🗑️ Удалить промокод"))
    builder.add(KeyboardButton(text="🔙 Назад"))
    builder.adjust(2, 1, 1)
    return builder.as_markup(resize_keyboard=True)

def get_admin_back_keyboard():
    """Клавиатура с кнопкой Назад для админа"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔙 Назад"))
    return builder.as_markup(resize_keyboard=True)

# Клавиатуры для библиотек
def get_libraries_main_keyboard(has_requirements: bool = False, is_script_running=False):
    """Главная клавиатура для библиотек"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📦 Показать библиотеки", callback_data="libraries_show")
    
    # Блокируем установку/удаление если скрипт запущен
    if not is_script_running:
        builder.button(text="📥 Установить библиотеку", callback_data="libraries_install")
        
        if has_requirements:
            builder.button(text="📁 Установить из requirements.txt", callback_data="libraries_install_requirements")
        
        builder.button(text="🗑️ Удалить библиотеку", callback_data="libraries_uninstall")
    else:
        builder.button(text="🚫 Установить библиотеку (скрипт запущен)", callback_data="libraries_locked")
        
        if has_requirements:
            builder.button(text="🚫 Установить из requirements.txt (скрипт запущен)", callback_data="libraries_locked")
        
        builder.button(text="🚫 Удалить библиотеку (скрипт запущен)", callback_data="libraries_locked")
    
    builder.button(text="💡 Справка", callback_data="libraries_help")
    builder.button(text="🔙 Назад к файлам", callback_data="back_to_files")
    builder.adjust(1)
    return builder.as_markup()

def get_libraries_back_keyboard():
    """Клавиатура с кнопкой Назад для библиотек"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="libraries_back")
    return builder.as_markup()

# Клавиатуры для платежной системы
def get_payment_keyboard():
    """Клавиатура для пополнения баланса"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Я перевел", callback_data="payment_made")
    builder.button(text="❌ Отмена", callback_data="cancel_payment")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_payment_keyboard(user_id: int, amount: int):
    """Клавиатура для админа при проверке платежа"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить платеж", callback_data=f"approve_payment_{user_id}_{amount}")
    builder.button(text="❌ Отклонить платеж", callback_data=f"reject_payment_{user_id}_{amount}")
    builder.adjust(1)
    return builder.as_markup()

# Дополнительные клавиатуры
def get_back_to_main_keyboard():
    """Клавиатура для возврата в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Главное меню", callback_data="back_to_main")
    return builder.as_markup()

def get_back_to_files_keyboard():
    """Клавиатура для возврата к файлам"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад к файлам", callback_data="back_to_files")
    return builder.as_markup()

def get_cancel_keyboard():
    """Клавиатура для отмены действий"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    return builder.as_markup()

def get_promo_activate_keyboard():
    """Клавиатура для активации промокода"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎫 Активировать промокод", callback_data="activate_promo")
    builder.button(text="🔙 Назад", callback_data="back_to_profile")
    builder.adjust(1)
    return builder.as_markup()

def get_back_to_profile_keyboard():
    """Клавиатура для возврата в профиль"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в профиль", callback_data="back_to_profile")
    return builder.as_markup()

# Новые клавиатуры для управления админами
def get_admin_management_keyboard():
    """Клавиатура для управления администраторами"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📋 Список админов"))
    builder.add(KeyboardButton(text="➕ Назначить админа"))
    builder.add(KeyboardButton(text="➖ Снять админа"))
    builder.add(KeyboardButton(text="🔙 Назад"))
    builder.adjust(2, 1, 1)
    return builder.as_markup(resize_keyboard=True)

def get_bot_connection_keyboard():
    """Клавиатура для подключения к ботам"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔗 Подключиться по ID"))
    builder.add(KeyboardButton(text="📋 Список активных ботов"))
    builder.add(KeyboardButton(text="🔙 Назад"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

# Клавиатура для отмены в промокодах
def get_promo_cancel_keyboard():
    """Клавиатура для отмены активации промокода"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_promo")
    return builder.as_markup()

# Клавиатура для выбора уровня админа
def get_admin_level_keyboard():
    """Клавиатура для выбора уровня администратора"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛡️ Модератор (Уровень 1)", callback_data="admin_level_1")
    builder.button(text="⚡ Админ (Уровень 2)", callback_data="admin_level_2")
    builder.button(text="👑 Владелец (Уровень 3)", callback_data="admin_level_3")
    builder.button(text="❌ Отмена", callback_data="cancel_admin_setup")
    builder.adjust(1)
    return builder.as_markup()

# Клавиатуры для шаблонов
def get_templates_keyboard():
    """Клавиатура с выбором шаблонов"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="🤖 Бот Авто-продаж | 30₽", 
        callback_data="template_shop_bot"
    ))
    builder.add(InlineKeyboardButton(
        text="🔐 Бот для продажи платных подписок | 30₽", 
        callback_data="template_subscription_bot"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 Назад", 
        callback_data="back_to_main"
    ))
    
    builder.adjust(1)
    return builder.as_markup()

def get_template_settings_keyboard(template_type: str):
    """Клавиатура настроек шаблона"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="⚙️ Конфигурация", 
        callback_data=f"template_settings_{template_type}"
    ))
    builder.add(InlineKeyboardButton(
        text="📁 Установить шаблон", 
        callback_data=f"template_install_{template_type}"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 Назад к шаблонам", 
        callback_data="back_to_templates"
    ))
    
    builder.adjust(1)
    return builder.as_markup()

def get_template_config_keyboard(template_type: str):
    """Клавиатура конфигурации шаблона"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="🤖 Токен бота", 
        callback_data=f"config_bot_token_{template_type}"
    ))
    builder.add(InlineKeyboardButton(
        text="👑 ID администраторов", 
        callback_data=f"config_admin_ids_{template_type}"
    ))
    builder.add(InlineKeyboardButton(
        text="👋 Приветствие", 
        callback_data=f"config_welcome_{template_type}"
    ))
    builder.add(InlineKeyboardButton(
        text="💬 Сообщение подписки", 
        callback_data=f"config_subscription_{template_type}"
    ))
    builder.add(InlineKeyboardButton(
        text="📢 Каналы для подписки", 
        callback_data=f"config_channels_{template_type}"
    ))
    builder.add(InlineKeyboardButton(
        text="💳 Способы пополнения", 
        callback_data=f"config_payment_{template_type}"
    ))
    builder.add(InlineKeyboardButton(
        text="💰 Валюта", 
        callback_data=f"config_currency_{template_type}"
    ))
    builder.add(InlineKeyboardButton(
        text="🎁 Реф награда", 
        callback_data=f"config_ref_reward_{template_type}"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 Назад к настройкам", 
        callback_data=f"template_settings_{template_type}"
    ))
    
    builder.adjust(2)
    return builder.as_markup()

def get_template_main_keyboard(template_type: str):
    """Основная клавиатура для шаблонов"""
    builder = ReplyKeyboardBuilder()
    
    if template_type == "shop_bot":
        builder.add(KeyboardButton(text="📦 Каталог"))
        builder.add(KeyboardButton(text="🏦 Кабинет"))
        builder.add(KeyboardButton(text="👥 Партнеры"))
        builder.add(KeyboardButton(text="ℹ️ О боте"))
        builder.add(KeyboardButton(text="👨‍💻 Админ-панель"))
        
    elif template_type == "subscription_bot":
        builder.add(KeyboardButton(text="📋 Тарифы"))
        builder.add(KeyboardButton(text="👤 Мои подписки"))
        builder.add(KeyboardButton(text="🏦 Кабинет"))
        builder.add(KeyboardButton(text="👨‍💻 Админ-панель"))
    
    builder.add(KeyboardButton(text="🔙 Главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_shop_admin_keyboard():
    """Админ-панель для бота магазина"""
    builder = ReplyKeyboardBuilder()
    
    builder.add(KeyboardButton(text="📦 Управление товарами"))
    builder.add(KeyboardButton(text="💳 Управление платежами"))
    builder.add(KeyboardButton(text="👥 Статистика"))
    builder.add(KeyboardButton(text="⚙️ Настройки"))
    builder.add(KeyboardButton(text="🔙 Назад"))
    
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_subscription_admin_keyboard():
    """Админ-панель для бота подписок"""
    builder = ReplyKeyboardBuilder()
    
    builder.add(KeyboardButton(text="📋 Управление тарифами"))
    builder.add(KeyboardButton(text="👤 Управление пользователями"))
    builder.add(KeyboardButton(text="💳 Платежи"))
    builder.add(KeyboardButton(text="📊 Статистика"))
    builder.add(KeyboardButton(text="⚙️ Настройки"))
    builder.add(KeyboardButton(text="🔙 Назад"))
    
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)