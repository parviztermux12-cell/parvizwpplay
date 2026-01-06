from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable, Union
from config import ADMIN_ID

class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем тип события
        if isinstance(event, Message) and event.text and event.text.startswith('/admin'):
            if event.from_user.id != ADMIN_ID:
                await event.answer("❌ Доступ запрещен")
                return
        
        # Для callback-запросов с админскими действиями
        elif isinstance(event, CallbackQuery):
            admin_callbacks = [
                "approve_payment_", "reject_payment_"
            ]
            
            if any(event.data.startswith(cb) for cb in admin_callbacks):
                if event.from_user.id != ADMIN_ID:
                    await event.answer("❌ Доступ запрещен", show_alert=True)
                    return
        
        return await handler(event, data)