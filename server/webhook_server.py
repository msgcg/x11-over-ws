import hmac
import hashlib
import os
import subprocess
import sys
from datetime import datetime
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# GitHub Secret Key (рекомендуется хранить в переменной окружения)
GITHUB_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', 'your_secret_key')
PROJECT_PATH = '/home/ubuntu/x11-over-ws'  # путь к проекту

def run_initial_deploy():
    """Функция, вызываемая при старте службы"""
    try:
        sys.path.append(os.path.join(PROJECT_PATH, 'server'))
        from deploy import run_deployment
        print("Запуск деплоя при старте службы...")
        run_deployment()
        print("Деплой завершён.")
    except Exception as e:
        print(f"Ошибка при деплое: {e}", file=sys.stderr)

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        abort(400, description="X-Hub-Signature-256 header is missing")

    sha_name, signature_hash = signature.split('=', 1)
    if sha_name != 'sha256':
        abort(501, description="Unsupported hash algorithm")

    mac = hmac.new(GITHUB_SECRET.encode('utf-8'), request.data, hashlib.sha256)
    if not hmac.compare_digest(mac.hexdigest(), signature_hash):
        abort(403, description="Invalid webhook signature")

    payload = request.json
    print(f"Payload получен: {payload}")

    if payload.get('ref') == 'refs/heads/main':
        try:
            os.chdir(PROJECT_PATH)
            print(f"Рабочая директория изменена на: {os.getcwd()}")

            # Выполняем git pull
            result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True)
            print("Git pull выполнен:")
            print(result.stdout)
            if result.stderr:
                print("Git pull ошибки:")
                print(result.stderr)

            # После git pull завершаем процесс для перезапуска службы systemd
            print("Завершаю процесс для перезапуска службы с новым кодом...")
            sys.exit(0)

        except subprocess.CalledProcessError as e:
            print(f"Ошибка git pull: {e}", file=sys.stderr)
            return jsonify({'message': 'Git pull failed', 'error': str(e)}), 500
        except Exception as e:
            print(f"Неизвестная ошибка: {e}", file=sys.stderr)
            return jsonify({'message': 'Internal server error', 'error': str(e)}), 500
    else:
        print(f"Push в ветку {payload.get('ref')}, игнорирую.")

    return jsonify({'message': 'Webhook received and processed'})

if __name__ == '__main__':
    # При старте службы вызываем деплой
    run_initial_deploy()
    app.run(host='0.0.0.0', port=5000)
