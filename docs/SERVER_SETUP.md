# Документация по установке и настройке сервера для X11-over-WS

Эта документация описывает шаги, необходимые для установки и настройки сервера для проекта X11-over-WS, чтобы обеспечить автоматическое развертывание после коммитов и доступ к виртуальному рабочему столу через веб-браузер.

## 1. Подготовка сервера

Предполагается, что у вас есть чистый неграфический сервер (например, Ubuntu Server, Debian, CentOS) с доступом по SSH.

### 1.1. Обновление системы

Перед началом установки обновите пакеты вашей системы:

```bash
sudo apt update
sudo apt upgrade -y
```
(Для CentOS/RHEL используйте `sudo yum update -y` или `sudo dnf update -y`)

### 1.2. Установка базовых компонентов

Установите Python 3, pip, Git и необходимые утилиты:

```bash
sudo apt install -y python3 python3-pip git curl
```
(Для CentOS/RHEL используйте `sudo yum install -y python3 python3-pip git curl` или `sudo dnf install -y python3 python3-pip git curl`)

### 1.3. Установка безголового X-сервера и XFCE4

Для запуска графического окружения без физического дисплея нам понадобится `Xvfb` и легкое окружение рабочего стола, такое как XFCE4.

```bash
sudo apt install -y xvfb xauth xfce4 xfce4-terminal
```
(Для CentOS/RHEL:
`sudo yum install -y xorg-x11-server-Xvfb xorg-x11-xauth xfce4-session xfce4-terminal`)

## Настройка аутентификации

Проект использует аутентификацию PAM (Pluggable Authentication Modules) для проверки учетных данных пользователей Linux.

### Установка зависимостей PAM

Для работы PAM необходимо установить соответствующие библиотеки. В Ubuntu/Debian это можно сделать следующей командой:

```bash
sudo apt-get install libpam-dev
```

### Настройка сертификатов SSL/TLS

Для безопасного WebSocket-соединения (WSS) требуются SSL/TLS сертификаты.

1.  **Размещение сертификатов**: Сертификаты должны быть расположены в папке `server/certs/`.
2.  **Имена файлов**: По умолчанию ожидаются файлы `fullchain1.pem` (цепочка сертификатов) и `privkey1.pem` (приватный ключ). Если вы используете другие имена файлов, их необходимо указать в `proxy.py`.
3.  **Получение сертификатов**:
    *   **Let's Encrypt**: Рекомендуется использовать Let's Encrypt для получения бесплатных SSL/TLS сертификатов. Вы можете использовать `certbot` для автоматического получения и обновления сертификатов. После получения сертификатов скопируйте `fullchain.pem` и `privkey.pem` в папку `server/certs/` и переименуйте их в `fullchain1.pem` и `privkey1.pem` соответственно.
    *   **Самоподписанные сертификаты**: Для целей разработки или тестирования можно сгенерировать самоподписанные сертификаты.

    Пример генерации самоподписанных сертификатов:

    ```bash
    openssl req -x509 -newkey rsa:4096 -nodes -keyout privkey1.pem -out fullchain1.pem -days 365
    ```

    Переместите сгенерированные `fullkey1.pem` и `privkey1.pem` в папку `server/certs/`.

4.  **Игнорирование Git**: Содержимое папки `server/certs/` игнорируется Git, чтобы избежать случайной публикации приватных ключей. Убедитесь, что файл `.gitkeep` присутствует в этой папке, чтобы Git отслеживал саму папку.

---

## 2. Развертывание проекта

### 2.1. Клонирование репозитория

Клонируйте ваш проект на сервер. Рекомендуется разместить его в директории, доступной для пользователя, от имени которого будет запускаться `webhook_server.py` (например, `/home/your_user/x11-over-ws` или `/opt/x11-over-ws`).

```bash
cd /home/your_user/ # или /opt/
git clone https://github.com/msgcg/x11-over-ws.git
cd x11-over-ws
```

### 2.2. Настройка виртуального окружения и зависимостей

Создайте виртуальное окружение и установите Python-зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 2.3. Настройка аутентификации PAM

Для аутентификации пользователей через PAM (Pluggable Authentication Modules) необходимо установить соответствующие системные библиотеки и Python-модуль.

```bash
sudo apt install -y libpam-dev
```

### 2.5. Настройка `webhook_deploy_server.py`

Файл `webhook_deploy_server.py` отвечает за прием вебхуков от GitHub и запуск процесса развертывания. Он должен быть запущен как служба `systemd`.

**Важно:** `webhook_deploy_server.py` не должен изменяться, так как он запускается как служба. Все изменения в логике развертывания должны быть в `deploy.py`.

Отредактируйте `webhook_deploy_server.py` (если это еще не сделано) и убедитесь, что `PROJECT_PATH` указывает на корневую директорию вашего проекта на сервере.

```python
# server/webhook_deploy_server.py
PROJECT_PATH = '/home/your_user/x11-over-ws' # Убедитесь, что это правильный путь
```

### 2.6. Настройка `webhook_server.py` (только для тестирования)

Файл `webhook_server.py` предназначен для тестирования и выполняет только `git pull` при получении вебхука. Он не запускает процесс развертывания.

```python
# server/webhook_server.py
PROJECT_PATH = '/home/your_user/x11-over-ws' # Убедитесь, что это правильный путь
```

### 2.7. Настройка секрета GitHub Webhook

Для безопасности вебхуков GitHub используйте секретный ключ. Этот ключ должен быть установлен как переменная окружения на сервере.

```bash
export GITHUB_WEBHOOK_SECRET='ВАШ_СЕКРЕТНЫЙ_КЛЮЧ'
```

**Важно:** Для постоянного хранения этой переменной окружения при запуске службы `systemd` вам нужно будет добавить ее в файл юнита `systemd` или использовать файл `.env` с `EnvironmentFile`.

### 2.5. Настройка `systemd` для `webhook_server.py`

Создайте файл юнита `systemd` для `webhook_server.py`. Например, `/etc/systemd/system/webhook.service`:

```ini
[Unit]
Description=GitHub Webhook Listener
After=network.target

[Service]
User=your_user # Замените на вашего пользователя
WorkingDirectory=/home/your_user/x11-over-ws/server # Путь к директории server
ExecStart=/home/your_user/x11-over-ws/.venv/bin/python3 webhook_server.py
Environment="GITHUB_WEBHOOK_SECRET=ВАШ_СЕКРЕТНЫЙ_КЛЮЧ" # Или используйте EnvironmentFile
Restart=always

[Install]
WantedBy=multi-user.target
```

После создания файла юнита, перезагрузите `systemd` и включите/запустите службу:

```bash
sudo systemctl daemon-reload
sudo systemctl enable webhook.service
sudo systemctl start webhook.service
sudo systemctl status webhook.service
```

### 2.6. Настройка `deploy.py`

Файл `deploy.py` содержит логику развертывания. Он запускается `webhook_server.py` после успешного `git pull`.

Убедитесь, что пути в `deploy.py` корректны и соответствуют структуре вашего проекта на сервере.

```python
# server/deploy.py
# ...
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
# ...
env['XAUTHORITY'] = os.path.join(PROJECT_ROOT, '.Xauthority') # Убедитесь, что этот путь корректен
# ...
```

## 3. Настройка Nginx (для доступа к клиенту)

Для доступа к клиентской части (HTML, JS) и проксированию WebSocket-соединений вам понадобится веб-сервер, такой как Nginx.

### 3.1. Установка Nginx

```bash
sudo apt install -y nginx
```
(Для CentOS/RHEL используйте `sudo yum install -y nginx` или `sudo dnf install -y nginx`)

### 3.2. Настройка Nginx для проекта
## 3.2.1 Настройка TLS (HTTPS) - Рекомендуется

Для безопасного соединения используйте Certbot для получения SSL-сертификата от Let's Encrypt:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain_or_server_ip
```
Следуйте инструкциям Certbot.
## 3.2.2 Настройка Nginx 

```nginx
server {
    listen 443 ssl;
    ssl on;
    server_name your_domain.com;
    ssl_certificate /etc/ssl/your_domain/fullchain.pem;
    ssl_certificate_key /etc/ssl/your_domain/privkey.pem;

    location / {
        root /home/your_user/x11-over-ws/client; # Путь к директории client
        index index.html;
        try_files $uri $uri/ =404;
    }

    location /display/ {
        proxy_pass http://127.0.0.1:8080; # Порт, на котором слушает proxy.py (ws_port)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade; # Использование переменной из 'map'
        proxy_set_header Host $host;
        proxy_read_timeout 86400s; # Увеличьте таймаут для длительных сессий
        proxy_send_timeout 86400s;
    }
}

server {
    listen 80;
    server_name your_domain.com;
    return 301 https://$host$request_uri;
}

```

**Важное замечание по ошибке `invalid Connection header: close`:**

Если вы сталкиваетесь с ошибкой `websockets.exceptions.InvalidUpgrade: invalid Connection header: close` в логах `proxy.py` или `426 Upgrade Required` в браузере, это, скорее всего, означает, что Nginx не передает корректные заголовки `Upgrade` и `Connection` для WebSocket-соединения. Убедитесь, что в вашей конфигурации Nginx присутствует `map $http_upgrade $connection_upgrade` и `proxy_set_header Connection $connection_upgrade;` в блоке `location /display/`.

Создайте символическую ссылку на этот файл в `sites-enabled` (если не хотите, просто переместите конфиг в папку `/etc/nginx/conf.d/`):

```bash
sudo ln -s /etc/nginx/sites-available/x11-over-ws /etc/nginx/sites-enabled/
sudo nginx -t # Проверьте синтаксис конфигурации
sudo systemctl restart nginx
```



## 4. Настройка GitHub Webhook

1.  Перейдите в репозиторий вашего проекта на GitHub.
2.  Нажмите "Settings" -> "Webhooks" -> "Add webhook".
3.  **Payload URL:** `http://your_domain_or_server_ip:5000/webhook` (или `https://` если настроен TLS для `webhook_server.py`)
4.  **Content type:** `application/json`
5.  **Secret:** Вставьте тот же секретный ключ, который вы установили в переменной окружения `GITHUB_WEBHOOK_SECRET` на сервере.
6.  **Which events would you like to trigger this webhook?** Выберите "Just the push event."
7.  Нажмите "Add webhook".

## 5. Проверка и запуск

После выполнения всех этих шагов:

1.  Убедитесь, что службы `webhook.service` и `nginx` запущены и активны.
2.  Сделайте коммит и пуш в ветку `main` вашего репозитория.
3.  Проверьте логи `webhook.service` (`sudo journalctl -u webhook.service -f`) и `webhook.log` в директории `server` вашего проекта, чтобы убедиться, что развертывание прошло успешно.
4.  Откройте `http://your_domain_or_server_ip` (или `https://`) в вашем браузере. Вы должны увидеть клиентскую часть и после подключения — виртуальный рабочий стол XFCE4.

## 6. Дополнительные замечания

*   **XAUTHORITY:** В `deploy.py` используется `.Xauthority` в корне проекта. Убедитесь, что этот файл создается и имеет правильные разрешения, если это необходимо для вашего сценария.
*   **Безопасность:** Откройте только необходимые порты (80, 443 для Nginx, 5000 для webhook_server, если он не проксируется Nginx) в вашем фаерволе. Порты X11 (6000+) и WebSocket (8080) должны быть доступны только локально (127.0.0.1).
*   **Логирование:** Регулярно проверяйте логи для отладки проблем.

Это исчерпывающее руководство должно помочь вам настроить сервер и обеспечить бесперебойное развертывание.