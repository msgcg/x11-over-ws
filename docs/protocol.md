# Протокол X-over-Ws

## Control (text JSON)

Сообщения вида:

```json
{"type":"NEW_CONN","conn":123}
{"type":"CLOSE_CONN","conn":123}
{"type":"PING"}
```

## Data (binary WebSocket frame)

`uint32_be(conn_id) || raw_payload`.

* Прокси преобразует все байты, приходящие по TCP от X-client, в бинарные фреймы с заголовком conn_id и шлёт в браузер.
* Браузер может отправлять binary frames обратно (conn_id + payload) для передачи в соответствующее TCP соединение.

Причина: X-сервер обслуживает много клиентов одновременно — нам нужен multiplex через один WS (простая и эффективная схема).