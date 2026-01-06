import firebase_admin
from firebase_admin import credentials, db
import json
from config import FIREBASE_CONFIG, ADMIN_LEVELS
from datetime import datetime, timedelta

class FirebaseDB:
    def __init__(self):
        try:
            cred = credentials.Certificate('service_account.json')
            firebase_admin.initialize_app(cred, FIREBASE_CONFIG)
            self.root = db.reference('/')
            print("✅ Firebase initialized successfully")
        except Exception as e:
            print(f"❌ Firebase initialization error: {e}")
    
    def create_user(self, user_id, first_name, username):
        user_ref = self.root.child('users').child(str(user_id))
        user_data = user_ref.get()
        
        if not user_data:
            user_data = {
                'user_id': str(user_id),
                'first_name': first_name,
                'username': username,
                'balance': 0,
                'hosting_plan': None,
                'hosting_expiry': None,
                'python_version': '3.9',
                'main_file': 'main.py',
                'script_status': 'stopped',
                'has_files': False,
                'files_count': 0,
                'libraries': [],
                'is_admin': False,
                'admin_level': 0,  # 0 - не админ, 1-3 уровни
                'is_banned': False,
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            user_ref.set(user_data)
            print(f"✅ Пользователь {user_id} создан в Firebase")
            return True
        else:
            print(f"ℹ️ Пользователь {user_id} уже существует в Firebase")
            return False
    
    def get_user(self, user_id):
        user_data = self.root.child('users').child(str(user_id)).get()
        if user_data and isinstance(user_data, dict):
            return user_data
        return None
    
    def update_user(self, user_id, updates):
        try:
            self.root.child('users').child(str(user_id)).update(updates)
            return True
        except Exception as e:
            print(f"❌ Error updating user: {e}")
            return False
    
    def get_all_users(self):
        users = self.root.child('users').get()
        return users or {}
    
    def set_user_has_files(self, user_id, has_files=True, files_count=0):
        """Устанавливаем флаг что у пользователя есть файлы"""
        return self.update_user(user_id, {
            'has_files': has_files,
            'files_count': files_count
        })
    
    def user_has_files(self, user_id):
        """Проверяем есть ли у пользователя файлы"""
        user_data = self.get_user(user_id)
        if user_data:
            return user_data.get('has_files', False)
        return False
    
    def update_balance(self, user_id, amount):
        try:
            user_ref = self.root.child('users').child(str(user_id))
            current_balance = user_ref.child('balance').get() or 0
            new_balance = max(0, current_balance + amount)
            user_ref.update({'balance': new_balance})
            return new_balance
        except Exception as e:
            print(f"❌ Error updating balance: {e}")
            return current_balance
    
    def add_library(self, user_id, library):
        try:
            user_ref = self.root.child('users').child(str(user_id))
            current_libraries = user_ref.child('libraries').get() or []
            if library not in current_libraries:
                current_libraries.append(library)
                user_ref.update({'libraries': current_libraries})
            return True
        except Exception as e:
            print(f"❌ Error adding library: {e}")
            return False
    
    def remove_library(self, user_id, library):
        try:
            user_ref = self.root.child('users').child(str(user_id))
            current_libraries = user_ref.child('libraries').get() or []
            if library in current_libraries:
                current_libraries.remove(library)
                user_ref.update({'libraries': current_libraries})
            return True
        except Exception as e:
            print(f"❌ Error removing library: {e}")
            return False

    # Новые методы для админ-панели
    def ban_user(self, user_id):
        """Забанить пользователя"""
        return self.update_user(user_id, {'is_banned': True})
    
    def unban_user(self, user_id):
        """Разбанить пользователя"""
        return self.update_user(user_id, {'is_banned': False})
    
    def set_admin(self, user_id, admin_level=1):
        """Назначить/снять администратора"""
        if admin_level == 0:
            return self.update_user(user_id, {
                'is_admin': False,
                'admin_level': 0
            })
        else:
            return self.update_user(user_id, {
                'is_admin': True,
                'admin_level': admin_level
            })
    
    def stop_user_script(self, user_id):
        """Остановить скрипт пользователя"""
        return self.update_user(user_id, {'script_status': 'stopped'})
    
    def update_hosting_price(self, plan_name, new_price):
        """Обновить цену хостинга"""
        try:
            self.root.child('hosting_plans').child(plan_name).child('price').set(new_price)
            return True
        except Exception as e:
            print(f"❌ Error updating hosting price: {e}")
            return False
    
    def update_hosting_duration(self, plan_name, new_duration_days):
        """Обновить длительность хостинга"""
        try:
            self.root.child('hosting_plans').child(plan_name).child('duration_days').set(new_duration_days)
            return True
        except Exception as e:
            print(f"❌ Error updating hosting duration: {e}")
            return False
    
    # Методы для промокодов
    def create_promo_code(self, code, reward_type, reward_value, uses_limit=1):
        """Создать промокод"""
        try:
            promo_data = {
                'code': code.upper(),
                'reward_type': reward_type,  # 'balance' или 'hosting'
                'reward_value': reward_value,
                'uses_limit': uses_limit,
                'used_count': 0,
                'used_by': [],
                'is_active': True,
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.root.child('promo_codes').child(code.upper()).set(promo_data)
            return True
        except Exception as e:
            print(f"❌ Error creating promo code: {e}")
            return False
    
    def use_promo_code(self, code, user_id):
        """Использовать промокод"""
        try:
            promo_ref = self.root.child('promo_codes').child(code.upper())
            promo_data = promo_ref.get()
            
            if not promo_data:
                return False, "Промокод не найден"
            
            if not promo_data.get('is_active', True):
                return False, "Промокод неактивен"
            
            if user_id in promo_data.get('used_by', []):
                return False, "Вы уже использовали этот промокод"
            
            if promo_data.get('used_count', 0) >= promo_data.get('uses_limit', 1):
                return False, "Лимит использований промокода исчерпан"
            
            # Применяем награду
            reward_type = promo_data.get('reward_type')
            reward_value = promo_data.get('reward_value')
            
            if reward_type == 'balance':
                self.update_balance(user_id, reward_value)
                message = f"Баланс пополнен на {reward_value}₽"
            elif reward_type == 'hosting':
                # Активируем хостинг
                expiry_date = (datetime.now() + timedelta(days=reward_value)).strftime("%d.%m.%Y %H:%M")
                self.update_user(user_id, {
                    'hosting_plan': f'FlixHost {reward_value} дней',
                    'hosting_expiry': expiry_date
                })
                message = f"Хостинг активирован на {reward_value} дней"
            else:
                return False, "Неизвестный тип награды"
            
            # Обновляем данные промокода
            promo_ref.update({
                'used_count': promo_data.get('used_count', 0) + 1,
                'used_by': promo_data.get('used_by', []) + [user_id]
            })
            
            return True, message
            
        except Exception as e:
            print(f"❌ Error using promo code: {e}")
            return False, "Ошибка при активации промокода"
    
    def get_promo_codes(self):
        """Получить все промокоды"""
        promos = self.root.child('promo_codes').get()
        return promos or {}
    
    def delete_promo_code(self, code):
        """Удалить промокод"""
        try:
            self.root.child('promo_codes').child(code.upper()).delete()
            return True
        except Exception as e:
            print(f"❌ Error deleting promo code: {e}")
            return False

    # Новые методы для управления админами
    def get_all_admins(self):
        """Получить всех администраторов"""
        users = self.get_all_users()
        admins = {}
        for user_id, user_data in users.items():
            if user_data.get('is_admin') and user_data.get('admin_level', 0) > 0:
                admins[user_id] = user_data
        return admins
    
    def can_user_manage(self, user_id, permission):
        """Проверить права пользователя"""
        user_data = self.get_user(user_id)
        if not user_data or not user_data.get('is_admin'):
            return False
        
        admin_level = user_data.get('admin_level', 0)
        
        # Владелец (уровень 3) - все права
        if admin_level >= 3:
            return True
        
        # Админ (уровень 2) - почти все права
        if admin_level >= 2:
            return permission in ['users', 'balance', 'hosting', 'promo', 'stats']
        
        # Модератор (уровень 1) - базовые права
        if admin_level >= 1:
            return permission in ['users', 'promo', 'stats']
        
        return False

firebase_db = FirebaseDB()