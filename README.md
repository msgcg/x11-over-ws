# X11 over WebSocket

Этот проект реализует прототип системы "X11 в браузере", где браузер выступает в роли X-сервера, а на сервере Ubuntu работает минимальный транспортный шлюз (proxy).

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

## Запуск прототипа

### Сервер

1. Установите необходимые зависимости:
   `pip install websockets aiofiles`
2. Запустите прокси-сервер:
   `python3 server/proxy.py --display 99 --ws-host 0.0.0.0 --ws-port 8080 --tcp-host 0.0.0.0`

### Клиент

Откройте `client/index.html` в браузере. Для удобства можно использовать простой веб-сервер (например, `python3 -m http.server` в директории `client`).

### Тестирование

После запуска сервера и клиента, вы можете попробовать подключиться к прокси с помощью X-клиента на сервере, указав `DISPLAY=localhost:99`.

Например:

`DISPLAY=localhost:99 xeyes`

В консоли браузера и на сервере должны появиться логи о новом TCP-соединении и передаче данных.