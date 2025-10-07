# ✅ Решение проблемы подключения WSL к Comet Browser

## Проблема
MCP-сервер на Python в WSL2 не мог подключиться к Comet Browser (форк Chromium) на Windows через порт 9222.

## Причина
Служба **IP Helper** (iphlpsvc) в Windows была остановлена, из-за чего правило `netsh portproxy` не работало.

Windows portproxy использует службу IP Helper для перенаправления портов. Comet слушает только на `127.0.0.1:9222`, поэтому нужен portproxy для проброса с `0.0.0.0:9222` → `127.0.0.1:9222`.

## ✅ Решение (РАБОТАЕТ)

### 1. Запустить Comet с remote debugging
```powershell
"C:\Users\work2\AppData\Local\Perplexity\Comet\Application\comet.exe" --remote-debugging-port=9222
```

### 2. Включить службу IP Helper
```powershell
# В PowerShell от администратора
net start iphlpsvc
```

### 3. Создать правило portproxy
```powershell
# В PowerShell от администратора
netsh interface portproxy add v4tov4 listenport=9222 listenaddress=0.0.0.0 connectport=9222 connectaddress=127.0.0.1
```

### 4. Добавить правило фаервола
```powershell
# В PowerShell от администратора
New-NetFirewallRule -DisplayName "WSL2 Chrome DevTools" -Direction Inbound -LocalPort 9222 -Protocol TCP -Action Allow
```

### 5. Проверить
```bash
# В WSL
curl http://172.23.128.1:9222/json/version
```

Должен вернуть JSON с информацией о браузере.

### 6. Использовать в Python
```python
import pychrome

# Подключиться к браузеру
browser = pychrome.Browser(url='http://172.23.128.1:9222')
print(browser.version())

# Работа с вкладками
tabs = browser.list_tab()
tab = tabs[0]
tab.start()

tab.call_method("Page.navigate", url="https://example.com")
```

## Проверка статуса

### В Windows PowerShell:
```powershell
# Проверить listener
netstat -ano | findstr ":9222"
# Должно быть:
#   TCP    0.0.0.0:9222     (portproxy)
#   TCP    127.0.0.1:9222   (Comet)

# Проверить правило portproxy
netsh interface portproxy show all

# Проверить службу IP Helper
Get-Service iphlpsvc
# Status должен быть Running
```

### В WSL:
```bash
# Проверить подключение
curl http://172.23.128.1:9222/json/version

# Проверить IP шлюза Windows
ip route | grep default
```

## Автозапуск службы IP Helper

Чтобы служба запускалась автоматически:
```powershell
# В PowerShell от администратора
Set-Service -Name iphlpsvc -StartupType Automatic
Start-Service iphlpsvc
```

## Troubleshooting

### Если после перезагрузки перестало работать:

1. Проверьте службу IP Helper:
```powershell
Get-Service iphlpsvc
# Если Stopped:
net start iphlpsvc
```

2. Проверьте правило portproxy:
```powershell
netsh interface portproxy show all
# Если пусто - пересоздайте правило
```

3. Проверьте, что Comet запущен с `--remote-debugging-port=9222`

### Если служба IP Helper не запускается:

Проверьте зависимости:
```powershell
Get-Service iphlpsvc | Select-Object -ExpandProperty DependentServices
sc.exe qc iphlpsvc
```

## Альтернативные решения

Если IP Helper не работает, можно использовать:
1. **SSH туннель** (требует SSH сервер на Windows)
2. **Python прокси** (`chrome_proxy.py` в этом репозитории)
3. **socat** (не может модифицировать HTTP заголовки, не подходит)

## Файлы в репозитории

- `fix_portproxy.ps1` - автоматическая настройка portproxy
- `diagnose_port.ps1` - диагностика проблем с портом 9222
- `chrome_proxy.py` - Python прокси (альтернатива portproxy)
- `fix_comet_wsl.md` - подробная документация всех способов

---

**Статус**: ✅ Решено
**Дата**: 2025-10-07
**Тестировано**: WSL2 Ubuntu 22.04 + Windows 11 + Comet Browser
