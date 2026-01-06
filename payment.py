from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from firebase_db import firebase_db
from keyboards import get_payment_keyboard, get_admin_payment_keyboard, get_cancel_keyboard, get_back_to_main_keyboard
from config import ADMIN_ID

router = Router()

class PaymentStates(StatesGroup):
    waiting_amount = State()
    waiting_photo = State()

# Хранилище для отслеживания обработанных платежей
processed_payments = set()

@router.callback_query(F.data == "replenish_balance")
async def replenish_balance_handler(callback: CallbackQuery, state: FSMContext):
    """Начало пополнения баланса"""
    await state.set_state(PaymentStates.waiting_amount)
    await callback.message.edit_text(
        "💳 <b>Пополнение баланса</b>\n\n"
        "Введите сумму пополнения (в рублях):",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(StateFilter(PaymentStates.waiting_amount), F.text)
async def process_payment_amount(message: Message, state: FSMContext):
    """Обработка введенной суммы"""
    try:
        amount = int(message.text.strip())
        
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
            
        if amount > 10000:
            await message.answer("❌ Максимальная сумма - 10,000₽")
            return
        
        await state.update_data(amount=amount)
        await state.set_state(PaymentStates.waiting_photo)
        
        await message.answer(
            f"💰 <b>Запрос на пополнение {amount}₽</b>\n\n"
            f"Переведите <b>{amount}₽</b> на один из счетов:\n\n"
            "🏦 <b>Альфа-Банк:</b>\n"
            "<code>2200153690449211</code>\n\n"
            "🏦 <b>Т-Банк:</b>\n"  
            "<code>2200701356585932</code>\n\n"
            "💡 <b>После перевода отправьте скриншот чека</b>",
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer("❌ Введите число (например: 100)")

@router.message(StateFilter(PaymentStates.waiting_photo), F.photo)
async def process_payment_photo(message: Message, state: FSMContext):
    """Обработка скриншота чека"""
    user_id = message.from_user.id
    data = await state.get_data()
    amount = data.get('amount', 0)
    
    user_data = firebase_db.get_user(str(user_id))
    if not user_data:
        await message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
        return
    
    await message.answer("✅ Чек получен! Ожидайте проверки администратора.")
    
    # Получаем всех администраторов
    admins = firebase_db.get_all_admins()
    
    # Отправляем всем админам
    for admin_id, admin_data in admins.items():
        try:
            admin_text = (
                "🎯 <b>Новый запрос на пополнение</b>\n\n"
                f"👤 <b>Пользователь:</b> {user_data.get('first_name', 'Неизвестно')}\n"
                f"🆔 <b>ID:</b> {user_id}\n"
                f"💰 <b>Сумма:</b> {amount}₽\n"
                f"📅 <b>Время:</b> {message.date.strftime('%d.%m.%Y %H:%M')}\n"
            )
            
            if user_data.get('username'):
                admin_text += f"📱 <b>Username:</b> @{user_data.get('username')}\n"
                
            admin_text += f"\n💳 <b>Текущий баланс:</b> {user_data.get('balance', 0)}₽"
            
            photo = message.photo[-1]
            await message.bot.send_photo(
                chat_id=int(admin_id),
                photo=photo.file_id,
                caption=admin_text,
                parse_mode="HTML",
                reply_markup=get_admin_payment_keyboard(user_id, amount)
            )
            
        except Exception as e:
            print(f"❌ Ошибка отправки админу {admin_id}: {e}")
    
    await state.clear()

@router.callback_query(F.data.startswith("approve_payment_"))
async def approve_payment_handler(callback: CallbackQuery):
    """Админ подтверждает платеж"""
    payment_key = callback.data
    
    # Проверяем, не обработан ли уже этот платеж
    if payment_key in processed_payments:
        await callback.answer("⚠️ Этот платеж уже обработан", show_alert=True)
        return
    
    try:
        parts = callback.data.replace("approve_payment_", "").split("_")
        user_id = int(parts[0])
        amount = int(parts[1])
        
        # Добавляем в обработанные
        processed_payments.add(payment_key)
        
        user_data = firebase_db.get_user(str(user_id))
        if not user_data:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        new_balance = firebase_db.update_balance(str(user_id), amount)
        
        try:
            await callback.bot.send_message(
                user_id,
                f"✅ <b>Баланс пополнен на {amount}₽</b>\n"
                f"💳 Новый баланс: {new_balance}₽",
                parse_mode="HTML"
            )
        except:
            pass
        
        # Уведомляем всех админов об одобрении
        admins = firebase_db.get_all_admins()
        for admin_id in admins:
            try:
                await callback.bot.send_message(
                    admin_id,
                    f"✅ <b>Платеж одобрен</b>\n\n"
                    f"👤 Пользователь: {user_data.get('first_name', 'Неизвестно')}\n"
                    f"🆔 ID: {user_id}\n"
                    f"💰 Сумма: {amount}₽\n"
                    f"💳 Новый баланс: {new_balance}₽",
                    parse_mode="HTML"
                )
            except:
                pass
        
        await callback.message.edit_text(
            f"✅ <b>Платеж подтвержден</b>\n\n"
            f"👤 Пользователь: {user_data.get('first_name', 'Неизвестно')}\n"
            f"🆔 ID: {user_id}\n"
            f"💰 Сумма: {amount}₽\n"
            f"💳 Новый баланс: {new_balance}₽",
            parse_mode="HTML"
        )
        
        await callback.answer("✅ Баланс пополнен")
        
    except Exception as e:
        await callback.answer("❌ Ошибка подтверждения", show_alert=True)

@router.callback_query(F.data.startswith("reject_payment_"))
async def reject_payment_handler(callback: CallbackQuery):
    """Админ отклоняет платеж"""
    payment_key = callback.data
    
    # Проверяем, не обработан ли уже этот платеж
    if payment_key in processed_payments:
        await callback.answer("⚠️ Этот платеж уже обработан", show_alert=True)
        return
    
    try:
        parts = callback.data.replace("reject_payment_", "").split("_")
        user_id = int(parts[0])
        amount = int(parts[1])
        
        # Добавляем в обработанные
        processed_payments.add(payment_key)
        
        user_data = firebase_db.get_user(str(user_id))
        if not user_data:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        try:
            await callback.bot.send_message(
                user_id,
                f"❌ Запрос на пополнение {amount}₽ отклонен"
            )
        except:
            pass
        
        # Уведомляем всех админов об отклонении
        admins = firebase_db.get_all_admins()
        for admin_id in admins:
            try:
                await callback.bot.send_message(
                    admin_id,
                    f"❌ <b>Платеж отклонен</b>\n\n"
                    f"👤 Пользователь: {user_data.get('first_name', 'Неизвестно')}\n"
                    f"🆔 ID: {user_id}\n"
                    f"💰 Сумма: {amount}₽",
                    parse_mode="HTML"
                )
            except:
                pass
        
        await callback.message.edit_text(f"❌ Платеж пользователя {user_id} отклонен")
        await callback.answer("❌ Платеж отклонен")
        
    except:
        await callback.answer("❌ Ошибка", show_alert=True)

@router.callback_query(F.data == "cancel_payment")
async def cancel_payment_handler(callback: CallbackQuery, state: FSMContext):
    """Отмена пополнения"""
    await state.clear()
    await callback.message.edit_text("❌ Пополнение отменено")
    await callback.answer()

@router.message(StateFilter(PaymentStates.waiting_photo))
async def wrong_photo_input(message: Message):
    """Неправильный ввод в состоянии фото"""
    await message.answer("❌ Отправьте скриншот чека")