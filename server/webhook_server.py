import hmac
import hashlib
import json
import subprocess
import sys
from flask import Flask, request, abort, Response
import os

app = Flask(__name__)

# Путь к корневой директории проекта
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Секретный ключ для проверки подписи GitHub Webhook
GITHUB_WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET')

@app.route('/webhook', methods=['POST'])
def webhook():
    if GITHUB_WEBHOOK_SECRET is None:
        print("Ошибка: Переменная окружения GITHUB_WEBHOOK_SECRET не установлена.", file=sys.stderr)
        abort(500)

    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        print("Ошибка: Отсутствует заголовок X-Hub-Signature-256.", file=sys.stderr)
        abort(400)

    if not request.is_json:
        print("Ошибка: Запрос не в формате JSON.", file=sys.stderr)
        abort(400)

    payload = request.data
    expected_signature = "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET.encode('utf-8'), payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        print("Ошибка: Неверная подпись вебхука.", file=sys.stderr)
        abort(403)

    event = request.headers.get('X-GitHub-Event')

    if event == 'push':
        print("Получен push-запрос. Выполняю git pull...", file=sys.stderr)
        try:
            # Переходим в корневую директорию проекта для выполнения git pull
            os.chdir(PROJECT_PATH)
            result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True)
            print(f"Git pull успешно выполнен: {result.stdout}", file=sys.stderr)
            if result.stderr:
                print(f"Git pull stderr: {result.stderr}", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при выполнении git pull: {e}", file=sys.stderr)
            print(f"Stdout: {e.stdout}", file=sys.stderr)
            print(f"Stderr: {e.stderr}", file=sys.stderr)
            abort(500)
        except Exception as e:
            print(f"Неизвестная ошибка при выполнении git pull: {e}", file=sys.stderr)
            abort(500)
    else:
        print(f"Получено событие GitHub: {event}. Игнорирую.", file=sys.stderr)

    return Response('{"message": "Webhook received"}', mimetype="application/json")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)