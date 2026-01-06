import asyncio
import os
import shutil
from datetime import datetime, timedelta
from firebase_db import firebase_db
from config import BOT_TOKEN
from utils.script_runner import script_runner
from aiogram import Bot
from keyboards import get_replenish_keyboard, get_blocked_keyboard

class HostingManager:
    def __init__(self):
        self.active_hostings = {}
        self.bot = Bot(token=BOT_TOKEN)
        self.notified_users = set()
        self.grace_period_users = {}
    
    async def check_hosting_expiry(self):
        """Check and update expired hostings"""
        users = firebase_db.get_all_users()
        current_date = datetime.now()
        
        print(f"🔍 Проверка истечения хостингов... Текущее время: {current_date}")
        
        expired_count = 0
        warned_count = 0
        deleted_count = 0
        
        for user_id, user_data in users.items():
            hosting_expiry = user_data.get('hosting_expiry')
            hosting_plan = user_data.get('hosting_plan')
            
            if hosting_plan and hosting_expiry:
                try:
                    expiry_date = datetime.strptime(hosting_expiry, "%d.%m.%Y %H:%M")
                    
                    time_left = expiry_date - current_date
                    time_left_hours = time_left.total_seconds() / 1
                    
                    print(f"🔍 Пользователь {user_id}:")
                    print(f"   Хостинг: {hosting_plan}")
                    print(f"   Истекает: {expiry_date}")
                    print(f"   Осталось часов: {time_left_hours:.1f}")
                    
                    # Предупреждение за 24 часа до истечения
                    if 0 < time_left_hours <= 24 and user_id not in self.notified_users:
                        try:
                            await self.bot.send_message(
                                user_id,
                                f"⚠️ ВНИМАНИЕ!\n\n"
                                f"До отключения хостинга осталось менее 24 часов!\n"
                                f"⏰ Истекает: {expiry_date.strftime('%d.%m.%Y в %H:%M')}\n\n"
                                f"Пополните баланс чтобы продлить хостинг.",
                                reply_markup=get_replenish_keyboard()
                            )
                            self.notified_users.add(user_id)
                            warned_count += 1
                            print(f"⚠️ Пользователь {user_id} предупрежден об окончании хостинга")
                        except Exception as e:
                            print(f"❌ Ошибка отправки предупреждения пользователю {user_id}: {e}")
                    
                    # Если хостинг истек
                    if current_date > expiry_date:
                        if user_id not in self.grace_period_users:
                            grace_period_end = current_date + timedelta(days=1)
                            self.grace_period_users[user_id] = grace_period_end
                            
                            try:
                                await self.bot.send_message(
                                    user_id,
                                    f"❌ Ваш хостинг не оплачен\nи поэтому был заблокирован\n\n"
                                    f"⚠️ У вас есть 24 часа чтобы оплатить хостинг.\n"
                                    f"⏰ После {grace_period_end.strftime('%d.%m.%Y в %H:%M')}\n"
                                    f"все файлы будут удалены без возможности восстановления!",
                                    reply_markup=get_blocked_keyboard()
                                )
                                print(f"📧 Пользователь {user_id} уведомлен о блокировке хостинга")
                            except Exception as e:
                                print(f"❌ Ошибка отправки уведомления о блокировке пользователю {user_id}: {e}")
                        
                        elif current_date > self.grace_period_users[user_id]:
                            user_folder = f"user_files/{user_id}"
                            if os.path.exists(user_folder):
                                shutil.rmtree(user_folder)
                                print(f"🗑️ Файлы пользователя {user_id} удалены")
                            
                            firebase_db.update_user(user_id, {
                                'hosting_plan': None,
                                'hosting_expiry': None,
                                'script_status': 'deleted',
                                'has_files': False,
                                'files_count': 0,
                                'main_file': 'main.py'
                            })
                            
                            del self.grace_period_users[user_id]
                            
                            try:
                                await self.bot.send_message(
                                    user_id,
                                    "💀 Все ваши файлы были удалены из-за неуплаты хостинга.\n\n"
                                    "Для восстановления доступа приобретите новый хостинг.",
                                    reply_markup=get_replenish_keyboard()
                                )
                                print(f"💀 Пользователь {user_id} уведомлен об удалении файлов")
                            except Exception as e:
                                print(f"❌ Ошибка отправки финального уведомления пользователю {user_id}: {e}")
                            
                            deleted_count += 1
                        
                        print(f"❌ Хостинг истек для пользователя {user_id}")
                        expired_count += 1
                        
                        if user_id in self.notified_users:
                            self.notified_users.remove(user_id)
                        
                except ValueError:
                    try:
                        expiry_date = datetime.strptime(hosting_expiry, "%d.%m.%Y")
                        if current_date > expiry_date:
                            if user_id not in self.grace_period_users:
                                grace_period_end = current_date + timedelta(days=1)
                                self.grace_period_users[user_id] = grace_period_end
                                
                                try:
                                    await self.bot.send_message(
                                        user_id,
                                        f"❌ Ваш хостинг не оплачен\nи поэтому был заблокирован\n\n"
                                        f"⚠️ У вас есть 24 часа чтобы оплатить хостинг.\n"
                                        f"⏰ После {grace_period_end.strftime('%d.%m.%Y в %H:%M')}\n"
                                        f"все файлы будут удалены без возможности восстановления!",
                                        reply_markup=get_blocked_keyboard()
                                    )
                                except Exception as e:
                                    print(f"❌ Ошибка отправки уведомления о блокировке пользователю {user_id}: {e}")
                            
                            elif current_date > self.grace_period_users[user_id]:
                                user_folder = f"user_files/{user_id}"
                                if os.path.exists(user_folder):
                                    shutil.rmtree(user_folder)
                                    print(f"🗑️ Файлы пользователя {user_id} удалены")
                                
                                firebase_db.update_user(user_id, {
                                    'hosting_plan': None,
                                    'hosting_expiry': None,
                                    'script_status': 'deleted',
                                    'has_files': False,
                                    'files_count': 0,
                                    'main_file': 'main.py'
                                })
                                
                                del self.grace_period_users[user_id]
                                
                                try:
                                    await self.bot.send_message(
                                        user_id,
                                        "💀 Все ваши файлы были удалены из-за неуплаты хостинга.\n\n"
                                        "Для восстановления доступа приобретите новый хостинг.",
                                        reply_markup=get_replenish_keyboard()
                                    )
                                except Exception as e:
                                    print(f"❌ Ошибка отправки финального уведомления пользователю {user_id}: {e}")
                                
                                deleted_count += 1
                            
                            print(f"❌ Хостинг истек для пользователя {user_id}")
                            expired_count += 1
                    except:
                        continue
        
        if expired_count > 0:
            print(f"🎯 Истекло хостингов: {expired_count}")
        if warned_count > 0:
            print(f"⚠️ Предупреждено пользователей: {warned_count}")
        if deleted_count > 0:
            print(f"💀 Удалено файлов пользователей: {deleted_count}")
        if expired_count == 0 and warned_count == 0 and deleted_count == 0:
            print("✅ Активных хостингов не истекло")
    
    async def start_expiry_checker(self):
        """Start periodic expiry checking"""
        print("🔄 Запуск проверки истечения хостингов (каждый час)")
        
        while True:
            await self.check_hosting_expiry()
            await asyncio.sleep(1)

hosting_manager = HostingManager()