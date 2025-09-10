from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

# Секретный ключ для проверки подписи GitHub (если используется)
# Установите его как переменную окружения или в конфигурационном файле
GITHUB_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', 'your_secret_key')

# Путь к вашему проекту на сервере
PROJECT_PATH = '/var/www/html/your_project' # Измените на актуальный путь

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        # Проверка секретного ключа (если используется)
        # if request.headers.get('X-Hub-Signature') is None:
        #     return jsonify({'message': 'X-Hub-Signature header missing'}), 400
        # # Здесь должна быть логика проверки подписи
        # # Для простоты пока пропустим, но в продакшене это обязательно!

        payload = request.json

        if payload and 'ref' in payload and payload['ref'] == 'refs/heads/main':
            print("Получен push в ветку main. Запускаю развертывание...")
            try:
                # Переходим в директорию проекта
                os.chdir(PROJECT_PATH)
                # Выполняем git pull
                pull_result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True)
                print("Git pull успешно выполнен:")
                print(pull_result.stdout)
                print(pull_result.stderr)

                # Здесь можно добавить команды для перезапуска сервера, запуска тестов и т.д.
                # Например, для Gunicorn/Supervisor:
                # subprocess.run(['sudo', 'systemctl', 'restart', 'your_service_name'], check=True)
                # print("Сервис перезапущен.")

                return jsonify({'message': 'Развертывание успешно завершено'}), 200
            except subprocess.CalledProcessError as e:
                print(f"Ошибка при выполнении команды: {e}")
                print(f"Stdout: {e.stdout}")
                print(f"Stderr: {e.stderr}")
                return jsonify({'message': f'Ошибка развертывания: {e.stderr}'}), 500
            except Exception as e:
                print(f"Неизвестная ошибка: {e}")
                return jsonify({'message': f'Неизвестная ошибка: {e}'}), 500
        else:
            return jsonify({'message': 'Неподдерживаемый тип события или ветка'}), 200
    return jsonify({'message': 'Метод не разрешен'}), 405

if __name__ == '__main__':
    # Запуск Flask-приложения
    # В продакшене используйте Gunicorn, Nginx/Apache и Supervisor
    app.run(host='0.0.0.0', port=5000)