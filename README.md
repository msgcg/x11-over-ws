# X11 over WebSocket

Этот проект реализует прототип системы "X11 в браузере", где браузер выступает в роли X-сервера, а на сервере Ubuntu работает минимальный транспортный шлюз (proxy).

## Философия проекта

Проект разработан с учетом гибкости и модульности. Основной `proxy.py` может быть запущен как в фоновом режиме (как служба `systemd`), так и в интерактивном режиме для отладки. Клиентская часть (браузер) взаимодействует с сервером через WebSocket Secure (WSS) для обеспечения безопасности.

## Структура проекта

```
x11-over-ws/
├─ server/
│  ├─ proxy.py                # основной TCP<->WS proxy
│  ├─ systemd/                # unit-файлы, скрипты деплоя
│  └─ requirements.txt
├─ client/
│  ├─ index.html
│  ├─ client.js               # базовый клиент (подключение к WS, протокол multiplex)
│  └─ ui/                     # React/Vue код или plain JS UI
├─ docs/
│  ├─ protocol.md             # спецификация X-over-Ws / framing / control messages
│  └─ architecture.md
├─ tools/
│  ├─ test_x_client.py        # тестовый TCP-клиент для отладки (имитирует X-клиент)
│  └─ utils.sh                # скрипты (генерация cookie, запуск тестов)
├─ README.md
```

## Сертификаты SSL/TLS

Для обеспечения безопасного соединения WebSocket (WSS) этот проект использует SSL/TLS сертификаты. Сертификаты должны быть расположены в папке `server/certs/`.

По умолчанию проект настроен на использование сертификатов Let's Encrypt. Вам потребуется получить `fullchain.pem` (цепочка сертификатов) и `privkey.pem` (приватный ключ) от Let's Encrypt и поместить их в эту папку. Убедитесь, что имена файлов соответствуют тем, что указаны в `proxy.py` (по умолчанию `fullchain1.pem` и `privkey1.pem`).

Если вы используете самоподписанные сертификаты, убедитесь, что они также находятся в этой папке и имеют соответствующие имена файлов.

**Важно:** Папка `server/certs/` должна существовать, но ее содержимое (сами сертификаты) игнорируется Git, чтобы предотвратить случайную публикацию приватных ключей. Убедитесь, что вы не добавляете сертификаты в систему контроля версий.

### Сервер

1.  Установите необходимые зависимости:
    `pip install websockets aiofiles`
2.  Запустите прокси-сервер:
    `python3 server/proxy.py --display 99 --ws-host 0.0.0.0 --ws-port 8080 --tcp-host 0.0.0.0`

### Клиент

Откройте `client/index.html` в браузере. Для удобства можно использовать простой веб-сервер (например, `python3 -m http.server` в директории `client`).

### Тестирование

После запуска сервера и клиента, вы можете попробовать подключиться к прокси с помощью X-клиента на сервере, указав `DISPLAY=localhost:99`.

Например:

`DISPLAY=localhost:99 xeyes`

В консоли браузера и на сервере должны появиться логи о новом TCP-соединении и передаче данных.

## Пример конфигурации Nginx

Для корректной работы WebSocket-соединений через Nginx, используйте следующую конфигурацию. Убедитесь, что `proxy_pass` указывает на `https` и соответствует порту, на котором слушает `proxy.py`.

```nginx
# Это "карта" для правильной установки заголовка Connection.
# Это самый надежный и официальный способ для проксирования WebSocket.
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

# основной сервер для домена (443)
server {
    listen 443 ssl http2; # Добавил http2 для производительности
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # Раздача статических файлов (вашего фронтенда)
    location / {
        root /home/ubuntu/x11-over-ws/client;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Проксирование WebSocket-соединений
    location /display/ {
        # ## ВАЖНО: Указываем https, а не http, так как proxy.py слушает на wss ##
        proxy_pass https://127.0.0.1:8080; # Изменено с http на https
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_read_timeout 86400s; # 24 часа
        proxy_send_timeout 86400s;
        # Если proxy.py использует самоподписанный сертификат, раскомментируйте следующую строку:
        # proxy_ssl_verify off;
    }
}

# Рекомендую добавить этот блок для автоматического редиректа с HTTP на HTTPS
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}