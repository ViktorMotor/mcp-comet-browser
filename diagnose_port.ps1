# Диагностика порта 9222 на Windows
Write-Host "=== Диагностика порта 9222 ===" -ForegroundColor Cyan

# Получить процесс, слушающий порт 9222
Write-Host "`n1. Процесс на порту 9222:" -ForegroundColor Yellow
$connections = Get-NetTCPConnection -LocalPort 9222 -State Listen -ErrorAction SilentlyContinue
if ($connections) {
    foreach ($conn in $connections) {
        $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        Write-Host "   PID: $($conn.OwningProcess)" -ForegroundColor White
        Write-Host "   Процесс: $($process.ProcessName)" -ForegroundColor White
        Write-Host "   Путь: $($process.Path)" -ForegroundColor White

        # Получить командную строку процесса
        $wmiProcess = Get-WmiObject Win32_Process -Filter "ProcessId = $($conn.OwningProcess)" -ErrorAction SilentlyContinue
        if ($wmiProcess) {
            Write-Host "   Командная строка: $($wmiProcess.CommandLine)" -ForegroundColor White
        }
    }
} else {
    Write-Host "   Порт 9222 не прослушивается" -ForegroundColor Red
}

# Проверить, запущен ли Comet
Write-Host "`n2. Процессы Comet/Chrome:" -ForegroundColor Yellow
$browserProcesses = Get-Process | Where-Object {
    $_.ProcessName -like "*comet*" -or
    $_.ProcessName -like "*chrome*"
}

if ($browserProcesses) {
    foreach ($proc in $browserProcesses) {
        Write-Host "   PID: $($proc.Id) - $($proc.ProcessName)" -ForegroundColor White
        Write-Host "   Путь: $($proc.Path)" -ForegroundColor Gray

        # Проверить, есть ли --remote-debugging-port в командной строке
        $wmi = Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue
        if ($wmi -and $wmi.CommandLine -like "*remote-debugging-port*") {
            Write-Host "   ✓ С remote debugging: $($wmi.CommandLine)" -ForegroundColor Green
        }
    }
} else {
    Write-Host "   Процессы браузера не найдены" -ForegroundColor Red
}

# Проверить правила фаервола
Write-Host "`n3. Правила фаервола для порта 9222:" -ForegroundColor Yellow
$firewallRules = Get-NetFirewallRule | Where-Object {
    $portFilter = $_ | Get-NetFirewallPortFilter -ErrorAction SilentlyContinue
    $portFilter -and ($portFilter.LocalPort -eq "9222")
}

if ($firewallRules) {
    foreach ($rule in $firewallRules) {
        Write-Host "   $($rule.DisplayName): $($rule.Enabled) - $($rule.Action)" -ForegroundColor White
    }
} else {
    Write-Host "   Правила не найдены" -ForegroundColor Yellow
}

# Тест подключения к localhost:9222
Write-Host "`n4. Тест подключения к localhost:9222:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9222/json/version" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✓ Успешно! Статус: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "   Ответ:" -ForegroundColor Gray
    Write-Host "   $($response.Content)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Ошибка: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Рекомендации ===" -ForegroundColor Cyan

if ($connections -and $connections[0].OwningProcess -ne 0) {
    $pid = $connections[0].OwningProcess
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue

    if ($proc.ProcessName -ne "comet" -and $proc.ProcessName -notlike "*chrome*") {
        Write-Host "⚠ Порт 9222 занят процессом $($proc.ProcessName) (PID $pid)" -ForegroundColor Yellow
        Write-Host "  Решение 1: Остановить процесс: Stop-Process -Id $pid -Force" -ForegroundColor White
        Write-Host "  Решение 2: Запустить Comet на другом порту: --remote-debugging-port=9223" -ForegroundColor White
    } elseif (-not ($wmiProcess.CommandLine -like "*remote-debugging-port*")) {
        Write-Host "⚠ Процесс браузера запущен без --remote-debugging-port" -ForegroundColor Yellow
        Write-Host "  Решение: Перезапустить с флагом --remote-debugging-port=9222" -ForegroundColor White
    } else {
        Write-Host "✓ Comet запущен правильно" -ForegroundColor Green
        Write-Host "  Если подключение из WSL не работает, используйте прокси:" -ForegroundColor White
        Write-Host "  python3 chrome_proxy.py" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠ Никакой процесс не слушает порт 9222" -ForegroundColor Yellow
    Write-Host "  Решение: Запустить Comet с флагом --remote-debugging-port=9222" -ForegroundColor White
}
