import hmac
import hashlib
import os
import sys
import subprocess
from threading import Thread
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

GITHUB_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', 'your_secret_key')
PROJECT_PATH = '/home/ubuntu/x11-over-ws'

def pull_and_restart():
    """Асинхронный git pull и завершение процесса для systemd"""
    try:
        os.chdir(PROJECT_PATH)
        print(f"Рабочая директория: {os.getcwd()}")
        result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True)
        print("Git pull выполнен:")
        print(result.stdout)
        if result.stderr:
            print("Ошибки git pull:")
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка git pull: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Неизвестная ошибка: {e}", file=sys.stderr)
    finally:
        print("Перезапуск службы через sys.exit(0)")
        sys.exit(0)

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
        # Запускаем git pull + sys.exit в отдельном потоке
        Thread(target=pull_and_restart).start()
        # Отвечаем GitHub сразу
        return jsonify({'message': 'Webhook received, deployment started'}), 200
    else:
        print(f"Push в ветку {payload.get('ref')}, игнорирую.")
        return jsonify({'message': 'Webhook received, ignored'}), 200

if __name__ == '__main__':
    # При старте службы можно вызвать деплой из deploy.py
    sys.path.append(os.path.join(PROJECT_PATH, 'server'))
    try:
        from deploy import run_deployment
        print("Запуск деплоя при старте службы...")
        run_deployment()
    except Exception as e:
        print(f"Ошибка деплоя при старте: {e}", file=sys.stderr)

    app.run(host='0.0.0.0', port=5000)
