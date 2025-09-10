import hmac
import hashlib
import os
import subprocess
import sys
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

GITHUB_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', 'your_secret_key')
PROJECT_PATH = '/home/ubuntu/x11-over-ws'
DEPLOY_SCRIPT_PATH = os.path.join(PROJECT_PATH, 'server')

def run_startup_deploy():
    """Выполнить deploy при старте службы"""
    try:
        sys.path.append(DEPLOY_SCRIPT_PATH)
        from deploy import run_deployment
        print("Запуск деплоя при старте службы...")
        run_deployment()
    except Exception as e:
        print(f"Ошибка деплоя при старте: {e}", file=sys.stderr)

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
            print(f"Рабочая директория: {os.getcwd()}")
            result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True)
            print("Git pull выполнен:")
            print(result.stdout)
            if result.stderr:
                print("Git pull ошибки:")
                print(result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Ошибка git pull: {e}")
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")

        # Завершаем процесс, чтобы systemd перезапустил его
        sys.exit(0)
    else:
        print(f"Push в ветку {payload.get('ref')}, игнорирую.")

    return jsonify({'message': 'Webhook received'}), 200

if __name__ == '__main__':
    # Автоматический запуск деплоя при старте службы
    run_startup_deploy()
    app.run(host='0.0.0.0', port=5000)
