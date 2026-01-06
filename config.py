import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = "8108389243:AAE1FRGaWmQXhwatZx5BYlaxZjD4bz3iNKA"
ADMIN_ID = 7526512670

# Уровни администраторов
ADMIN_LEVELS = {
    "owner": 3,      # Владелец - все права
    "admin": 2,      # Админ - почти все права
    "moderator": 1   # Модератор - базовые права
}

# Firebase config
FIREBASE_CONFIG = {
    "databaseURL": "https://botcreator-2b64d-default-rtdb.firebaseio.com/"
}

# Hosting plans with different durations
HOSTING_PLANS = {
    "Free": {
        "name": "FlixHost Free 24 hours",
        "os": "Debian",
        "price": 0,
        "storage": "2 GB",
        "ram": "250 MB",
        "duration_days": 1,
        "python_versions": ["3.8", "3.9", "3.10", "3.11"]
    },
    "7days": {
        "name": "FlixHost 7 дней",
        "os": "Debian",
        "price": 60,
        "storage": "2 GB",
        "ram": "250 MB",
        "duration_days": 7,
        "python_versions": ["3.8", "3.9", "3.10", "3.11"]
    },
    "14days": {
        "name": "FlixHost 14 дней",
        "os": "Debian",
        "price": 100,
        "storage": "2 GB", 
        "ram": "250 MB",
        "duration_days": 14,
        "python_versions": ["3.8", "3.9", "3.10", "3.11"]
    },
    "30days": {
        "name": "FlixHost 30 дней",
        "os": "Debian",
        "price": 150,
        "storage": "2 GB",
        "ram": "250 MB",
        "duration_days": 30,
        "python_versions": ["3.8", "3.9", "3.10", "3.11"]
    }
}

# Python versions
PYTHON_VERSIONS = ["3.8", "3.9", "3.10", "3.11"]

# Шаблоны ботов
BOT_TEMPLATES = {
    "shop_bot": {
        "name": "🤖 Бот Авто-продаж",
        "price": 30,
        "description": "Готовый бот для продажи товаров с каталогом, кабинетом и партнерской программой",
        "folder": "templates/shop_bot/main.py",
        "features": [
            "📦 Каталог товаров",
            "🏦 Личный кабинет", 
            "👥 Партнерская программа",
            "📊 Статистика",
            "👨‍💻 Админ-панель"
        ]
    },
    "subscription_bot": {
        "name": "🔐 Бот для продажи платных подписок", 
        "price": 30,
        "description": "Бот для продажи подписок с тарифами и управлением доступом",
        "folder": "templates/subscription_bot/main.py",
        "features": [
            "📋 Система тарифов",
            "👤 Управление подписками",
            "💳 Платежная система",
            "📊 Аналитика",
            "👨‍💻 Админ-панель"
        ]
    }
}