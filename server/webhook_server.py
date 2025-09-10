from flask import Flask, request, jsonify, abort # Добавим abort
import subprocess
import os
import sys
import hmac # Добавим для HMAC
import hashlib # Добавим для хеширования

app = Flask(__name__)

# Секретный ключ для проверки подписи GitHub
# Установите его как переменную окружения или в конфигурационном файле
GITHUB_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', 'your_secret_key').encode('utf-8') # Важно: должен быть байтовой строкой

# Путь к вашему проекту на сервере
PROJECT_PATH = '/home/ubuntu/x11-over-ws' # Убедитесь, что это ваш актуальный путь

@app.route('/webhook', methods=['POST'])
def webhook():
    print("Получен запрос на /webhook", file=sys.stderr)
    if request.method == 'POST':
        # Получаем подпись из заголовка
        signature = request.headers.get('X-Hub-Signature-256') # GitHub теперь использует X-Hub-Signature-256
        if not signature:
            print("Заголовок X-Hub-Signature-256 отсутствует.", file=sys.stderr)
            abort(400, 'X-Hub-Signature-256 header missing')

        # Получаем тело запроса в сыром виде
        # request.data содержит сырые байты запроса
        payload_body = request.data

        # Вычисляем ожидаемую подпись
        # 'sha256=' - это префикс, который GitHub добавляет к подписи
        expected_signature = 'sha256=' + hmac.new(GITHUB_SECRET, payload_body, hashlib.sha256).hexdigest()

        # Сравниваем подписи
        if not hmac.compare_digest(expected_signature, signature):
            print("Неверная подпись вебхука.", file=sys.stderr)
            abort(401, 'Invalid signature') # 401 Unauthorized

        # Если подпись верна, продолжаем обработку
        payload = request.json
        print(f"Payload получен: {payload}", file=sys.stderr)

        if payload and 'ref' in payload and payload['ref'] == 'refs/heads/main':
            print("Получен push в ветку main. Запускаю развертывание...", file=sys.stderr)
            try:
                # Переходим в директорию проекта
                os.chdir(PROJECT_PATH)
                print(f"Рабочая директория изменена на: {os.getcwd()}", file=sys.stderr)
                # Выполняем git pull
                pull_result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True)
                print("Git pull успешно выполнен:", file=sys.stderr)
                print(pull_result.stdout, file=sys.stderr)
                print(pull_result.stderr, file=sys.stderr)

                # Здесь можно добавить команды для перезапуска сервера, запуска тестов и т.д.
                # Например, для Gunicorn/Supervisor:
                # subprocess.run(['sudo', 'systemctl', 'restart', 'your_service_name'], check=True)
                # print("Сервис перезапущен.", file=sys.stderr)

                return jsonify({'message': 'Развертывание успешно завершено'}), 200
            except subprocess.CalledProcessError as e:
                print(f"Ошибка при выполнении команды: {e}", file=sys.stderr)
                print(f"Stdout: {e.stdout}", file=sys.stderr)
                print(f"Stderr: {e.stderr}", file=sys.stderr)
                return jsonify({'message': f'Ошибка развертывания: {e.stderr}'}), 500
            except Exception as e:
                print(f"Неизвестная ошибка: {e}", file=sys.stderr)
                return jsonify({'message': f'Неизвестная ошибка: {e}'}), 500
        else:
            print("Неподдерживаемый тип события или ветка.", file=sys.stderr)
            return jsonify({'message': 'Неподдерживаемый тип события или ветка'}), 200
    print("Метод не разрешен.", file=sys.stderr)
    return jsonify({'message': 'Метод не разрешен'}), 405

if __name__ == '__main__':
    # Запуск Flask-приложения
    # В продакшене используйте Gunicorn, Nginx/Apache и Supervisor
    app.run(host='0.0.0.0', port=5000)
