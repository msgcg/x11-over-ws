import subprocess
import sys
from datetime import datetime
import os # Добавляем импорт os

# Определяем базовый путь проекта относительно deploy.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')

def run_deployment():
    print("Запускаю скрипт развертывания...", file=sys.stderr)
    
    try:
        # Остановка существующих процессов proxy.py и xfce4-session
        print("Останавливаю существующие процессы proxy.py и xfce4-session...", file=sys.stderr)
        subprocess.run(["pkill", "-f", "proxy.py"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "xfce4-session"], stderr=subprocess.DEVNULL)
        print("Существующие процессы остановлены.", file=sys.stderr)

        #Установка зависимостей внутри текущего виртуального окружения
        print("Устанавливаю зависимости из файла {}...".format(os.path.join(PROJECT_ROOT, "requirements.txt")), file=sys.stderr)
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", os.path.join(PROJECT_ROOT, "requirements.txt")], capture_output=True, text=True, check=True)
            print(f"Установка python зависимостей: {result.stdout}", file=sys.stderr)
            if result.stderr:
                print(f"Ошибки установки зависимостей: {result.stderr}", file=sys.stderr)
            with open('webhook.log', 'a') as f:
                f.write(f"[{datetime.now()}] Installing requirements.txt...\n")
                f.write(f"Pip install stdout:\n{result.stdout}\n")
                if result.stderr:
                    f.write(f"Pip install stderr:\n{result.stderr}\n")
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при установке зависимостей: {e}", file=sys.stderr)
            print(f"Stdout: {e.stdout}", file=sys.stderr)
            print(f"Stderr: {e.stderr}", file=sys.stderr)
            with open('webhook.log', 'a') as f:
                f.write(f"[{datetime.now()}] Error installing requirements: {e}\n")
                f.write(f"Stdout: {e.stdout}\n")
                f.write(f"Stderr: {e.stderr}\n")
            raise # Перевыбрасываем исключение, чтобы оно было обработано выше

        # Запуск server/proxy.py в фоновом режиме
        print("Запускаю server/proxy.py в фоновом режиме...", file=sys.stderr)
        try:
            # Устанавливаем переменные окружения для X11
            env = os.environ.copy()
            env['DISPLAY'] = '127.0.0.1:99' # Используем display 99, как в Plan.txt
            env['XAUTHORITY'] = os.path.join(PROJECT_ROOT, '.Xauthority') # Предполагаем, что .Xauthority будет в корне проекта

            subprocess.run([sys.executable, os.path.join(BASE_DIR, "proxy.py"), "--display", "99"], 
                             env=env) # Передаем переменные окружения
            print("server/proxy.py запущен.", file=sys.stderr)
            with open('webhook.log', 'a') as f:
                f.write(f"[{datetime.now()}] server/proxy.py started in background.\n")
        except Exception as e:
            print(f"Ошибка при запуске server/proxy.py: {e}", file=sys.stderr)
            with open('webhook.log', 'a') as f:
                f.write(f"[{datetime.now()}] Error starting server/proxy.py: {e}\n")
            raise

        # Инструкции по запуску тестовых X-приложений на сервере
        print("Запускаю XFCE4...", file=sys.stderr)
        try:
            # Запуск XFCE4 в фоновом режиме
            env = os.environ.copy()
            env['DISPLAY'] = '127.0.0.1:99'
            env['XAUTHORITY'] = os.path.join(PROJECT_ROOT, '.Xauthority')

            subprocess.Popen(["xfce4-session"], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL, 
                             preexec_fn=os.setsid,
                             env=env) # Передаем переменные окружения
            print("XFCE4 запущен.", file=sys.stderr)
            with open('webhook.log', 'a') as f:
                f.write(f"[{datetime.now()}] XFCE4 started in background.\n")
        except Exception as e:
            print(f"Ошибка при запуске XFCE4: {e}", file=sys.stderr)
            with open('webhook.log', 'a') as f:
                f.write(f"[{datetime.now()}] Error starting XFCE4: {e}\n")
            raise

        print("Развертывание завершено.", file=sys.stderr)
        with open('webhook.log', 'a') as f:
            f.write(f"[{datetime.now()}] Deployment script executed successfully.\n")

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении развертывания: {e}", file=sys.stderr)
        print(f"Stdout: {e.stdout}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        with open('webhook.log', 'a') as f:
            f.write(f"[{datetime.now()}] Error executing deployment script: {e}\n")
            f.write(f"Stdout: {e.stdout}\n")
            f.write(f"Stderr: {e.stderr}\n")
        # Остановка webhook.service при ошибке развертывания
        print("Останавливаю webhook.service из-за ошибки развертывания...", file=sys.stderr)
        subprocess.run(["sudo", "systemctl", "stop", "webhook.service"], stderr=subprocess.DEVNULL)
        print("webhook.service остановлен.", file=sys.stderr)
    except Exception as e:
        print(f"Неизвестная ошибка в скрипте развертывания: {e}", file=sys.stderr)
        with open('webhook.log', 'a') as f:
            f.write(f"[{datetime.now()}] Unknown error in deployment script: {e}\n")
        # Остановка webhook.service при неизвестной ошибке
        print("Останавливаю webhook.service из-за неизвестной ошибки развертывания...", file=sys.stderr)
        subprocess.run(["sudo", "systemctl", "stop", "webhook.service"], stderr=subprocess.DEVNULL)
        print("webhook.service остановлен.", file=sys.stderr)

if __name__ == '__main__':
    run_deployment()
