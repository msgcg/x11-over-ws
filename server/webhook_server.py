import hmac
import hashlib
import os
import subprocess
import sys
from datetime import datetime
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# GitHub Secret Key (replace with your actual secret key)
# It's recommended to load this from an environment variable for security
GITHUB_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', 'your_secret_key') # Use a strong, random key

PROJECT_PATH = '/home/ubuntu/x11-over-ws' # Убедитесь, что это правильный путь к вашему проекту

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        # Verify the signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            print("Отсутствует заголовок X-Hub-Signature-256", file=sys.stderr)
            abort(400, description="X-Hub-Signature-256 header is missing")

        # Extract the hash from the signature header
        sha_name, signature_hash = signature.split('=', 1)
        if sha_name != 'sha256':
            print(f"Неподдерживаемый алгоритм хеширования: {sha_name}", file=sys.stderr)
            abort(501, description="Unsupported hash algorithm")

        # Calculate the HMAC digest
        mac = hmac.new(GITHUB_SECRET.encode('utf-8'), request.data, hashlib.sha256)
        if not hmac.compare_digest(mac.hexdigest(), signature_hash):
            print("Неверная подпись вебхука", file=sys.stderr)
            abort(403, description="Invalid webhook signature")

        payload = request.json
        print(f"Payload получен: {payload}")

        if payload.get('ref') == 'refs/heads/main':
            print("Получен push в ветку main. Запускаю развертывание...")
            try:
                # Change to the project directory
                os.chdir(PROJECT_PATH)
                print(f"Рабочая директория изменена на: {os.getcwd()}")

                # Execute git pull
                result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True)
                print("Git pull успешно выполнен:")
                print(result.stdout)
                if result.stderr:
                    print("Git pull ошибки:")
                    print(result.stderr)

                import sys
                sys.path.append(PROJECT_PATH + '/server')
                from deploy import run_deployment
                # Check if git pull actually fetched new content
                if "Already up to date." not in result.stdout:
                    print("Обнаружены новые изменения. Завершаю процесс для перезапуска службы с новым кодом...")
                    sys.exit(0) # Завершаем процесс, чтобы systemd перезапустил его с новым кодом

                # If we reach here, either no new changes, or the service just restarted with new code.
                # Now, run the deployment logic.
                import sys
                sys.path.append(PROJECT_PATH + '/server')
                from deploy import run_deployment
                run_deployment()

            except subprocess.CalledProcessError as e:
                print(f"Ошибка при выполнении git pull: {e}", file=sys.stderr)
                print(f"Stdout: {e.stdout}", file=sys.stderr)
                print(f"Stderr: {e.stderr}", file=sys.stderr)
                with open('webhook.log', 'a') as f:
                    f.write(f"[{datetime.now()}] Error executing git pull: {e}\n")
                    f.write(f"Stdout: {e.stdout}\n")
                    f.write(f"Stderr: {e.stderr}\n")
                return jsonify({'message': 'Deployment failed', 'error': str(e)}), 500
            except Exception as e:
                print(f"Неизвестная ошибка: {e}", file=sys.stderr)
                with open('webhook.log', 'a') as f:
                    f.write(f"[{datetime.now()}] Unknown error: {e}\n")
                return jsonify({'message': 'Internal server error', 'error': str(e)}), 500
        else:
            print(f"Получен push в ветку {payload.get('ref')}, игнорирую.")
        return jsonify({'message': 'Webhook received and processed'})
    else:
        abort(405) # Method Not Allowed

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
