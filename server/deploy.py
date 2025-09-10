import subprocess
import sys
from datetime import datetime

def run_deployment():
    print("Запускаю скрипт развертывания...", file=sys.stderr)
    
    try:
        # Установка зависимостей внутри текущего виртуального окружения
        print("Устанавливаю зависимости из requirements.txt...", file=sys.stderr)
        with open('webhook.log', 'a') as f:
            f.write(f"[{datetime.now()}] installing requirements.txt...\n")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "/home/ubuntu/x11-over-ws/requirements.txt"])

        # Пример перезапуска сервиса (если нужно)
        # result = subprocess.run(['sudo', 'systemctl', 'restart', 'your_project_service'], capture_output=True, text=True, check=True)
        # print(f"Перезапуск сервиса: {result.stdout}", file=sys.stderr)
        # if result.stderr:
        #     print(f"Ошибки перезапуска сервиса: {result.stderr}", file=sys.stderr)

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
    except Exception as e:
        print(f"Неизвестная ошибка в скрипте развертывания: {e}", file=sys.stderr)
        with open('webhook.log', 'a') as f:
            f.write(f"[{datetime.now()}] Unknown error in deployment script: {e}\n")

if __name__ == '__main__':
    run_deployment()
