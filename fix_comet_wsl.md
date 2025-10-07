# Решение проблемы подключения WSL к Comet Browser

## Диагноз
Comet Browser (форк Chromium) с `--remote-debugging-port=9222` проверяет **Host header** в HTTP запросах и принимает только:
- `localhost:9222`
- `127.0.0.1:9222`

Когда запросы приходят из WSL с IP `172.23.128.1`, браузер получает `Host: 172.23.128.1:9222` и закрывает соединение без ответа.

## Решение 1: SSH туннель (РЕКОМЕНДУЕТСЯ)

### Из WSL2:
```bash
# Создать туннель
ssh -L 9222:127.0.0.1:9222 user@172.23.128.1 -N -f

# Теперь подключаться к localhost:9222 в WSL
curl http://localhost:9222/json/version
```

Где `user` - ваш пользователь Windows (нужен SSH сервер на Windows).

## Решение 2: socat для проксирования

### В WSL2 установить socat:
```bash
sudo apt update && sudo apt install -y socat
```

### Запустить прокси:
```bash
socat TCP-LISTEN:9223,fork,reuseaddr "PROXY:172.23.128.1:127.0.0.1:9222|TCP:172.23.128.1:9222"
```

Это НЕ РАБОТАЕТ напрямую, так как нужно модифицировать HTTP заголовки.

## Решение 3: Python прокси с модификацией заголовков (РАБОЧЕЕ)

Создайте файл `chrome_proxy.py`:

```python
#!/usr/bin/env python3
import socket
import threading

LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 9223
TARGET_HOST = '172.23.128.1'
TARGET_PORT = 9222

def handle_client(client_socket):
    try:
        # Подключиться к целевому серверу
        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_socket.connect((TARGET_HOST, TARGET_PORT))

        def forward(source, destination, modify_host=False):
            try:
                while True:
                    data = source.recv(4096)
                    if not data:
                        break

                    # Модифицировать Host header в запросах от клиента
                    if modify_host:
                        data_str = data.decode('utf-8', errors='ignore')
                        # Заменить Host header
                        data_str = data_str.replace(
                            f'Host: {LISTEN_HOST}:{LISTEN_PORT}',
                            f'Host: 127.0.0.1:{TARGET_PORT}'
                        )
                        data_str = data_str.replace(
                            f'Host: localhost:{LISTEN_PORT}',
                            f'Host: 127.0.0.1:{TARGET_PORT}'
                        )
                        # Если Host содержит IP WSL шлюза
                        import re
                        data_str = re.sub(
                            r'Host: \d+\.\d+\.\d+\.\d+:' + str(LISTEN_PORT),
                            f'Host: 127.0.0.1:{TARGET_PORT}',
                            data_str
                        )
                        data = data_str.encode('utf-8')

                    destination.sendall(data)
            except Exception as e:
                print(f"Forward error: {e}")
            finally:
                source.close()
                destination.close()

        # Создать потоки для двунаправленного проксирования
        client_to_server = threading.Thread(
            target=forward, args=(client_socket, target_socket, True)
        )
        server_to_client = threading.Thread(
            target=forward, args=(target_socket, client_socket, False)
        )

        client_to_server.start()
        server_to_client.start()

        client_to_server.join()
        server_to_client.join()

    except Exception as e:
        print(f"Error handling client: {e}")
        client_socket.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LISTEN_HOST, LISTEN_PORT))
    server.listen(5)
    print(f"Proxy listening on {LISTEN_HOST}:{LISTEN_PORT}")
    print(f"Forwarding to {TARGET_HOST}:{TARGET_PORT} with Host header fix")

    try:
        while True:
            client_socket, addr = server.accept()
            print(f"Connection from {addr}")
            client_handler = threading.Thread(
                target=handle_client, args=(client_socket,)
            )
            client_handler.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.close()

if __name__ == '__main__':
    main()
```

### Запуск:
```bash
python3 chrome_proxy.py
```

### Использование:
```bash
# В другом терминале WSL
curl http://localhost:9223/json/version

# В Python коде
import pychrome
browser = pychrome.Browser(url="http://127.0.0.1:9223")
```

## Решение 4: Запустить Comet с правильным флагом

### На Windows запустить Comet так:
```powershell
comet.exe --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0
```

⚠️ **ВНИМАНИЕ**: Это небезопасно! Порт будет доступен из сети.

Лучше:
```powershell
comet.exe --remote-debugging-port=9222 --remote-allow-origins=*
```

Или указать конкретный origin:
```powershell
comet.exe --remote-debugging-port=9222 --remote-allow-origins="http://172.23.128.1:9222"
```

## Решение 5: Windows Port Proxy + Host Rewrite (не работает)

Port proxy НЕ может модифицировать HTTP заголовки, поэтому это решение не подходит.

## Проверка правил фаервола

Если нужно создать правило:

```powershell
# В PowerShell от администратора
New-NetFirewallRule -DisplayName "Comet CDP" -Direction Inbound -LocalPort 9222 -Protocol TCP -Action Allow
```

## Проверить, работает ли

После применения любого решения:

```bash
# Из WSL
curl http://localhost:9223/json/version  # Если используете прокси
# Или
curl http://localhost:9222/json/version  # Если используете туннель

# Должен вернуть JSON:
# {
#    "Browser": "Chrome/xxx",
#    "Protocol-Version": "1.3",
#    "User-Agent": "...",
#    "V8-Version": "...",
#    "WebKit-Version": "...",
#    "webSocketDebuggerUrl": "ws://..."
# }
```
