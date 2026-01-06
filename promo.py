from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from firebase_db import firebase_db
from keyboards import get_profile_keyboard, get_main_keyboard, get_cancel_keyboard

router = Router()

class PromoStates(StatesGroup):
    waiting_promo_code = State()

@router.callback_query(F.data == "activate_promo")
async def activate_promo_callback(callback: CallbackQuery, state: FSMContext):
    """Активация промокода"""
    await state.set_state(PromoStates.waiting_promo_code)
    await callback.message.edit_text(
        "🎫 <b>Активация промокода</b>\n\n"
        "Введите промокод:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(PromoStates.waiting_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    """Обработка промокода"""
    user_id = message.from_user.id
    promo_code = message.text.strip().upper()
    
    success, result_message = firebase_db.use_promo_code(promo_code, str(user_id))
    
    if success:
        # Получаем обновленные данные пользователя
        user_data = firebase_db.get_user(str(user_id))
        
        # Если активирован хостинг, меняем клавиатуру
        if "хостинг" in result_message.lower():
            await message.answer(
                f"✅ {result_message}",
                reply_markup=get_main_keyboard(user_data)
            )
        else:
            await message.answer(f"✅ {result_message}")
    else:
        await message.answer(f"❌ {result_message}")
    
    await state.clear()

@router.callback_query(F.data == "cancel_action")
async def cancel_promo_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена активации промокода"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Активация промокода отменена",
        reply_markup=get_profile_keyboard()
    )
    await callback.answer()