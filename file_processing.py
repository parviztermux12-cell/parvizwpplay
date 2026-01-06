import zipfile
import os
import aiofiles
import asyncio
from typing import Dict, List
import base64
import shutil

class FileProcessor:
    @staticmethod
    async def extract_zip(file_content: bytes, user_id: int) -> Dict[str, str]:
        """Extract ZIP file and return file contents - убираем лишние папки"""
        files = {}
        temp_zip = f"temp_{user_id}.zip"
        
        try:
            print(f"📦 Начинаем распаковку ZIP для пользователя {user_id}")
            
            # Save zip file temporarily
            async with aiofiles.open(temp_zip, 'wb') as f:
                await f.write(file_content)
            print("✅ Временный ZIP файл сохранен")
            
            # Extract files
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                print(f"📁 Найдено файлов в архиве: {len(file_list)}")
                print(f"📋 Содержимое архива: {file_list}")
                
                # Определяем корневую папку
                root_folder = None
                for file_info in zip_ref.infolist():
                    if not file_info.is_dir():
                        parts = file_info.filename.split('/')
                        if len(parts) > 1:
                            root_folder = parts[0]
                            break
                
                print(f"🔍 Корневая папка в архиве: {root_folder}")
                
                for file_info in zip_ref.infolist():
                    if not file_info.is_dir():
                        original_path = file_info.filename
                        
                        # Убираем корневую папку если она есть
                        if root_folder and original_path.startswith(root_folder + '/'):
                            clean_path = original_path[len(root_folder) + 1:]
                        else:
                            clean_path = original_path
                        
                        print(f"📄 Обрабатываем файл: {original_path} -> {clean_path}")
                        
                        with zip_ref.open(file_info) as file:
                            content = file.read()
                            # Encode binary content to base64 for potential storage
                            encoded_content = base64.b64encode(content).decode('utf-8')
                            files[clean_path] = encoded_content
            
            print(f"✅ Успешно распаковано {len(files)} файлов")
            
            # Clean up
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
                print("✅ Временный файл удален")
                
        except Exception as e:
            print(f"❌ Ошибка extracting ZIP: {e}")
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
        
        return files
    
    @staticmethod
    async def save_files_locally(files: Dict[str, str], user_id: int):
        """Save files to local directory for user - сохраняем без лишних папок"""
        user_folder = f"user_files/{user_id}"
        
        # Очищаем старые файлы
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
            print(f"✅ Очищена старая папка пользователя {user_id}")
        
        os.makedirs(user_folder, exist_ok=True)
        
        saved_count = 0
        for filepath, encoded_content in files.items():
            try:
                # Создаем полный путь к файлу
                full_path = os.path.join(user_folder, filepath)
                
                # Создаем директории если нужно
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                content = base64.b64decode(encoded_content)
                
                async with aiofiles.open(full_path, 'wb') as f:
                    await f.write(content)
                saved_count += 1
                print(f"💾 Файл сохранен локально: {filepath} -> {full_path}")
            except Exception as e:
                print(f"❌ Ошибка сохранения файла {filepath}: {e}")
        
        print(f"✅ Всего сохранено локально: {saved_count} файлов")
        
        # Покажем структуру сохраненных файлов
        print(f"📁 Структура папки {user_folder}:")
        FileProcessor._print_directory_structure(user_folder)
        
        return saved_count
    
    @staticmethod
    def _print_directory_structure(startpath):
        """Print directory structure for debugging"""
        for root, dirs, files in os.walk(startpath):
            level = root.replace(startpath, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f'{indent}{os.path.basename(root)}/')
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f'{subindent}{file}')
    
    @staticmethod
    def get_file_list_from_local(user_id: int) -> str:
        """Get file list from local storage with full paths"""
        user_folder = f"user_files/{user_id}"
        if not os.path.exists(user_folder):
            return "❌ Файлы не найдены"
        
        files = []
        for root, dirs, filenames in os.walk(user_folder):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                # Получаем относительный путь от папки пользователя
                rel_path = os.path.relpath(full_path, user_folder)
                files.append(rel_path)
        
        if not files:
            return "❌ Файлы не найдены"
        
        file_list = "📁 Ваши файлы:\n\n"
        for filepath in sorted(files):
            file_list += f"📄 {filepath}\n"
        
        file_list += f"\n📊 Всего файлов: {len(files)}"
        return file_list
    
    @staticmethod
    def find_python_files(user_id: int) -> List[str]:
        """Find all Python files in user's directory"""
        user_folder = f"user_files/{user_id}"
        if not os.path.exists(user_folder):
            return []
        
        python_files = []
        for root, dirs, filenames in os.walk(user_folder):
            for filename in filenames:
                if filename.endswith('.py'):
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, user_folder)
                    python_files.append(rel_path)
        
        return sorted(python_files)
    
    @staticmethod
    def file_exists(user_id: int, filename: str) -> bool:
        """Check if file exists in user's directory (with relative path)"""
        user_folder = f"user_files/{user_id}"
        if not os.path.exists(user_folder):
            return False
        
        # Проверяем файл с относительным путем
        file_path = os.path.join(user_folder, filename)
        return os.path.exists(file_path)
    
    @staticmethod
    def get_file_path(user_id: int, filename: str) -> str:
        """Get full path to file"""
        user_folder = f"user_files/{user_id}"
        return os.path.join(user_folder, filename)
    
    @staticmethod
    def has_any_files(user_id: int) -> bool:
        """Check if user has any files"""
        user_folder = f"user_files/{user_id}"
        if not os.path.exists(user_folder):
            return False
        
        # Проверяем, есть ли хотя бы один файл в любой поддиректории
        for root, dirs, files in os.walk(user_folder):
            if files:
                return True
        return False
    
    @staticmethod
    def count_files(user_id: int) -> int:
        """Count all files in user's directory"""
        user_folder = f"user_files/{user_id}"
        if not os.path.exists(user_folder):
            return 0
        
        file_count = 0
        for root, dirs, files in os.walk(user_folder):
            file_count += len(files)
        
        return file_count

    @staticmethod
    def check_requirements_file(user_id: int) -> bool:
        """Проверить наличие requirements.txt"""
        user_folder = f"user_files/{user_id}"
        requirements_file = os.path.join(user_folder, "requirements.txt")
        return os.path.exists(requirements_file)

    @staticmethod
    def get_requirements_content(user_id: int) -> str:
        """Получить содержимое requirements.txt"""
        user_folder = f"user_files/{user_id}"
        requirements_file = os.path.join(user_folder, "requirements.txt")
        
        if not os.path.exists(requirements_file):
            return None
        
        try:
            with open(requirements_file, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return None

file_processor = FileProcessor()