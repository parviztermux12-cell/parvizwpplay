import asyncio
import os
import psutil
import aiofiles
from typing import Optional
import subprocess
import signal
from datetime import datetime

class ScriptRunner:
    def __init__(self):
        self.running_processes = {}
    
    def get_python_executable(self, python_version: str) -> str:
        """Get the correct Python executable based on version"""
        if python_version.startswith('3.'):
            return "python3"
        elif python_version in ["python3", "python"]:
            return python_version
        else:
            return "python3"
    
    async def start_script(self, user_id: int, script_path: str, python_version: str = "3.9"):
        """Start Python script for real - УМНЫЕ ЛОГИ"""
        try:
            print(f"🚀 START_SCRIPT called with:")
            print(f"   user_id: {user_id}")
            print(f"   script_path: {script_path}")
            print(f"   python_version: {python_version}")
            
            if not os.path.isabs(script_path):
                script_path = os.path.abspath(script_path)
                print(f"🔧 Converted to absolute path: {script_path}")
            
            if not os.path.exists(script_path):
                error_msg = f"Файл не найден: {script_path}"
                print(f"❌ {error_msg}")
                return False, error_msg
            
            python_executable = self.get_python_executable(python_version)
            print(f"🔧 Используем Python: {python_executable}")
            
            logs_dir = f"logs/user_{user_id}"
            os.makedirs(logs_dir, exist_ok=True)
            
            log_file = f"{logs_dir}/script.log"
            
            if os.path.exists(log_file):
                os.remove(log_file)
            
            script_dir = os.path.dirname(script_path)
            
            print(f"🚀 Запускаем скрипт:")
            print(f"   📄 Файл: {script_path}")
            print(f"   📁 Директория: {script_dir}")
            print(f"   🐍 Python: {python_executable}")
            print(f"   ✅ Файл существует: {os.path.exists(script_path)}")
            print(f"   📝 Логи: {log_file}")
            
            process = await asyncio.create_subprocess_exec(
                python_executable, script_path,
                cwd=script_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE
            )
            
            self.running_processes[user_id] = process
            
            asyncio.create_task(self._log_output(user_id, process, log_file))
            
            return True, "Скрипт запущен успешно"
            
        except Exception as e:
            error_msg = f"Ошибка запуска: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    async def stop_script(self, user_id: int):
        """Stop running script"""
        if user_id in self.running_processes:
            process = self.running_processes[user_id]
            try:
                print(f"🛑 Останавливаем скрипт пользователя {user_id}")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    print(f"⚠️ Принудительная остановка скрипта пользователя {user_id}")
                    process.kill()
                    await process.wait()
            except ProcessLookupError:
                print(f"ℹ️ Процесс пользователя {user_id} уже завершен")
                pass
            finally:
                self.running_processes.pop(user_id, None)
            return True
        return False
    
    def _is_error_message(self, line: str) -> bool:
        """Определяем, является ли сообщение настоящей ошибкой"""
        line_lower = line.lower()
        
        # Информационные сообщения, которые НЕ являются ошибками
        info_keywords = [
            'info', 'debug', 'warning', 'start', 'run', 'polling',
            'update', 'handled', 'duration', 'connected', 'ready',
            'initialized', 'loading', 'success', 'completed'
        ]
        
        # Настоящие ошибки
        error_keywords = [
            'error', 'exception', 'traceback', 'failed', 'failure',
            'critical', 'fatal', 'unhandled', 'crash', 'broken'
        ]
        
        # Проверяем на наличие ключевых слов ошибок
        for error_word in error_keywords:
            if error_word in line_lower:
                return True
        
        # Если есть ключевые слова INFO, но нет ERROR - это не ошибка
        for info_word in info_keywords:
            if info_word in line_lower and not any(error_word in line_lower for error_word in error_keywords):
                return False
        
        return False
    
    async def _log_output(self, user_id: int, process, log_file: str):
        """Log script output to single file - УМНЫЕ ЛОГИ"""
        try:
            async with aiofiles.open(log_file, 'w', encoding='utf-8') as log:
                start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                await log.write(f"=== СКРИПТ ЗАПУСКАЕТЬСЯ  ===\n")
                await log.write(f"Время: {start_time}\n")
                await log.write(f"Пользователь: {user_id}\n")
                await log.write("=" * 40 + "\n\n")
                await log.flush()
                
                while True:
                    # Read stdout - обычные сообщения
                    try:
                        stdout = await asyncio.wait_for(process.stdout.readline(), timeout=1.0)
                        if stdout:
                            line = stdout.decode('utf-8', errors='ignore').strip()
                            if line:  # Не пишем пустые строки
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                await log.write(f"[{timestamp}] {line}\n")
                                await log.flush()
                                print(f"[USER {user_id} STDOUT] {line}")
                    except asyncio.TimeoutError:
                        pass
                    
                    # Read stderr - проверяем настоящие ли это ошибки
                    try:
                        stderr = await asyncio.wait_for(process.stderr.readline(), timeout=1.0)
                        if stderr:
                            line = stderr.decode('utf-8', errors='ignore').strip()
                            if line:  # Не пишем пустые строки
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                
                                # Определяем тип сообщения
                                if self._is_error_message(line):
                                    await log.write(f"[{timestamp}] [ERROR] {line}\n")
                                    print(f"[USER {user_id} STDERR] ❌ {line}")
                                else:
                                    await log.write(f"[{timestamp}] [INFO] {line}\n")
                                    print(f"[USER {user_id} STDERR] ℹ️ {line}")
                                
                                await log.flush()
                    except asyncio.TimeoutError:
                        pass
                    
                    # Check if process ended
                    if process.returncode is not None:
                        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        await log.write(f"\n" + "=" * 40 + "\n")
                        await log.write(f"=== СКРИПТ ЗАВЕРШЕН ===\n")
                        await log.write(f"Время: {end_time}\n")
                        await log.write(f"Код завершения: {process.returncode}\n")
                        
                        # Добавляем информацию о результате
                        if process.returncode == 0:
                            await log.write(f"Результат: УСПЕШНО ✅\n")
                        else:
                            await log.write(f"Результат: ОШИБКА ❌ (код: {process.returncode})\n")
                        
                        await log.write("=" * 40 + "\n")
                        await log.flush()
                        print(f"✅ Скрипт пользователя {user_id} завершен с кодом: {process.returncode}")
                        break
                        
        except Exception as e:
            print(f"❌ Ошибка логирования для пользователя {user_id}: {e}")
    
    def is_script_running(self, user_id: int) -> bool:
        """Check if script is running"""
        if user_id in self.running_processes:
            process = self.running_processes[user_id]
            return process.returncode is None
        return False
    
    def get_script_status(self, user_id: int) -> str:
        """Get script status"""
        if user_id in self.running_processes:
            process = self.running_processes[user_id]
            if process.returncode is None:
                return "running"
            else:
                return f"stopped (code: {process.returncode})"
        return "stopped"
    
    def get_resource_usage(self, user_id: int) -> dict:
        """Get resource usage for user"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        return {
            "cpu": f"{cpu_percent}%",
            "ram_used": f"{memory.used / (1024 * 1024):.1f} MB",
            "ram_total": f"{memory.total / (1024 * 1024):.1f} MB",
            "storage_used": "0 GB",
            "storage_total": "2 GB"
        }
    
    async def get_logs(self, user_id: int) -> Optional[str]:
        """Get script logs"""
        log_file = f"logs/user_{user_id}/script.log"
        if os.path.exists(log_file):
            async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                return await f.read()
        return None
    
    async def get_errors(self, user_id: int) -> Optional[str]:
        """Get only error logs"""
        log_file = f"logs/user_{user_id}/script.log"
        if os.path.exists(log_file):
            async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                # Фильтруем только строки с ошибками
                error_lines = []
                for line in content.split('\n'):
                    if '[ERROR]' in line:
                        error_lines.append(line)
                return '\n'.join(error_lines) if error_lines else None
        return None

script_runner = ScriptRunner()