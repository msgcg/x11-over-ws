# tools/test_x_client.py
import asyncio
import struct
import zlib

async def test_x_client(host='127.0.0.1', port=6099):
    print(f"Подключаюсь к X-серверу на {host}:{port}...")
    try:
        reader, writer = await asyncio.open_connection(host, port)
        print("Подключение установлено.")

        # Пример отправки данных: имитация X11 handshake
        # Это очень упрощенный пример, реальный handshake сложнее.
        # Обычно это 12 байт: байт порядка, 1 байт паддинга, 2 байта версии протокола, 2 байта длины авторизации, 2 байта длины данных авторизации.
        # Здесь просто отправляем что-то, чтобы прокси мог это обработать.
        data_to_send = b'\x6c\x00\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00' # Пример X11 handshake (little-endian, version 11.0)
        print(f"Отправляю {len(data_to_send)} байт: {data_to_send.hex()}")
        writer.write(data_to_send)
        await writer.drain()

        # Чтение ответа от прокси
        print("Ожидаю данные от прокси...")
        while True:
            response = await reader.read(8192)
            if not response:
                print("Соединение закрыто прокси.")
                break
            print(f"Получено {len(response)} байт от прокси: {response.hex()}")

    except ConnectionRefusedError:
        print(f"Ошибка: Отказано в подключении к {host}:{port}. Убедитесь, что proxy.py запущен.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        if 'writer' in locals() and writer.can_write_eof():
            writer.close()
            await writer.wait_closed()
            print("Соединение закрыто.")

if __name__ == '__main__':
    asyncio.run(test_x_client())