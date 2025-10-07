# Fix Windows Port Proxy for WSL2 access to Chrome DevTools
# Run this as Administrator

Write-Host "=== Fixing Port Proxy for Chrome DevTools ===" -ForegroundColor Cyan

# Remove existing rule
Write-Host "`nRemoving old portproxy rule..." -ForegroundColor Yellow
netsh interface portproxy delete v4tov4 listenport=9222 listenaddress=0.0.0.0

# Add new rule
Write-Host "Adding new portproxy rule..." -ForegroundColor Yellow
netsh interface portproxy add v4tov4 listenport=9222 listenaddress=0.0.0.0 connectport=9222 connectaddress=127.0.0.1

# Show all rules
Write-Host "`nCurrent portproxy rules:" -ForegroundColor Green
netsh interface portproxy show all

# Check if listening
Write-Host "`nListening status:" -ForegroundColor Green
$listener = Get-NetTCPConnection -LocalPort 9222 -State Listen -ErrorAction SilentlyContinue | Where-Object {$_.LocalAddress -eq "0.0.0.0"}
if ($listener) {
    Write-Host "✓ Port 9222 is listening on 0.0.0.0" -ForegroundColor Green
} else {
    Write-Host "✗ Port 9222 is NOT listening on 0.0.0.0" -ForegroundColor Red
    Write-Host "  This might be because:" -ForegroundColor Yellow
    Write-Host "  1. Another service already occupies port 9222" -ForegroundColor Yellow
    Write-Host "  2. Portproxy service is not running" -ForegroundColor Yellow
    Write-Host "`n  Try restarting the portproxy service:" -ForegroundColor Yellow
    Write-Host "  net stop iphlpsvc && net start iphlpsvc" -ForegroundColor Gray
}

# Add firewall rule
Write-Host "`nChecking firewall rule..." -ForegroundColor Yellow
$fwRule = Get-NetFirewallRule -DisplayName "WSL2 Chrome DevTools" -ErrorAction SilentlyContinue
if (-not $fwRule) {
    Write-Host "Creating firewall rule..." -ForegroundColor Yellow
    New-NetFirewallRule -DisplayName "WSL2 Chrome DevTools" -Direction Inbound -LocalPort 9222 -Protocol TCP -Action Allow -Profile Any
    Write-Host "✓ Firewall rule created" -ForegroundColor Green
} else {
    Write-Host "✓ Firewall rule already exists" -ForegroundColor Green
}

Write-Host "`n=== Test from WSL ===" -ForegroundColor Cyan
Write-Host "Run this in WSL:" -ForegroundColor White
Write-Host "  curl http://172.23.128.1:9222/json/version" -ForegroundColor Gray
