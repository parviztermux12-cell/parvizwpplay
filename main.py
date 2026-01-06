import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
import subprocess

from config import BOT_TOKEN, BOT_TEMPLATES  # Добавьте импорт BOT_TEMPLATES
from handlers.start import router as start_router
from handlers.profile import router as profile_router
from handlers.hosting import router as hosting_router
from handlers.files import router as files_router
from handlers.admin import router as admin_router
from handlers.payment import router as payment_router
from handlers.libraries import router as libraries_router
from handlers.promo import router as promo_router
from handlers.templates import router as templates_router
from utils.hosting_manager import hosting_manager

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# ДОБАВЬТЕ ЭТУ ПРОВЕРКУ ПЕРЕД ОСНОВНОЙ ФУНКЦИЕЙ
print("=" * 50)
print("🔍 ПРОВЕРКА ШАБЛОНОВ ПРИ ЗАПУСКЕ")
print("=" * 50)
print(f"Доступные шаблоны: {list(BOT_TEMPLATES.keys())}")
for key, value in BOT_TEMPLATES.items():
    print(f"Шаблон '{key}': {value['name']}")
    
    # Проверяем существование папки
    template_folder = f"templates/{key}"
    exists = os.path.exists(template_folder)
    print(f"  Папка {template_folder}: {'✅ СУЩЕСТВУЕТ' if exists else '❌ НЕ СУЩЕСТВУЕТ'}")
    
    if exists:
        files = os.listdir(template_folder)
        print(f"  Файлы: {files}")
print("=" * 50)

class CommandMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Если сообщение начинается с команды (/start, /admin и т.д.)
        if event.text and event.text.startswith('/'):
            # Очищаем состояние FSM для команды
            state = data.get('state')
            if state:
                current_state = await state.get_state()
                if current_state:
                    await state.clear()
                    logger.info(f"Очищено состояние {current_state} для команды {event.text}")
        
        return await handler(event, data)

def create_directories():
    directories = ['logs', 'user_files', 'templates/shop_bot', 'templates/subscription_bot']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"✅ Создана директория: {directory}")

async def install_requirements():
    """Установка библиотек из requirements.txt при запуске"""
    try:
        if os.path.exists('requirements.txt'):
            logger.info("📦 Обнаружен requirements.txt, устанавливаю библиотеки...")
            process = await asyncio.create_subprocess_exec(
                'pip', 'install', '-r', 'requirements.txt',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("✅ Все библиотеки из requirements.txt успешно установлены")
            else:
                error = stderr.decode().strip()
                logger.error(f"❌ Ошибка установки библиотек: {error}")
        else:
            logger.info("ℹ️ Файл requirements.txt не найден")
    except Exception as e:
        logger.error(f"❌ Ошибка при установке библиотек: {e}")

async def main():
    create_directories()
    
    # Устанавливаем библиотеки при запуске
    await install_requirements()
    
    storage = MemoryStorage()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)

    # ДОБАВЛЯЕМ MIDDLEWARE ПЕРВЫМ
    dp.message.middleware(CommandMiddleware())
    
    routers = [
        start_router,
        profile_router, 
        hosting_router,
        files_router,
        libraries_router,
        payment_router,
        promo_router,
        admin_router,
        templates_router,
    ]
    
    for router in routers:
        dp.include_router(router)
        logger.info(f"✅ Router {router.name} loaded")

    asyncio.create_task(hosting_manager.start_expiry_checker())

    logger.info("🤖 Бот запускается...")
    logger.info("✅ Все системы готовы к работе!")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())