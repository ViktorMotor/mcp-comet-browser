@echo off
REM ========================================
REM MCP Comet Browser - WSL Startup Script
REM ========================================
REM
REM This script automates the startup process for WSL users:
REM 1. Starts Python proxy (windows_proxy.py) on port 9224
REM 2. Waits for proxy to initialize
REM 3. Launches Comet browser with remote debugging on port 9222
REM
REM After running this script, start the MCP server in WSL:
REM   python3 server.py
REM
REM ========================================

echo.
echo [MCP Comet Browser] Starting WSL environment...
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Check if windows_proxy.py exists
if not exist "windows_proxy.py" (
    echo [ERROR] windows_proxy.py not found in current directory!
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Step 1: Start Python proxy in a new window
echo [1/3] Starting CDP proxy on port 9224...
start "MCP CDP Proxy" python windows_proxy.py

REM Step 2: Wait for proxy to initialize
echo [2/3] Waiting for proxy to initialize...
timeout /t 3 /nobreak >nul

REM Step 3: Start Comet browser with remote debugging
echo [3/3] Starting Comet browser on port 9222...
set COMET_PATH=%LOCALAPPDATA%\Perplexity\Comet\Application\comet.exe

if not exist "%COMET_PATH%" (
    echo [WARNING] Comet not found at default path:
    echo   %COMET_PATH%
    echo.
    echo Please edit this script and set the correct COMET_PATH
    pause
    exit /b 1
)

start "" "%COMET_PATH%" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222

echo.
echo ========================================
echo [SUCCESS] WSL environment ready!
echo ========================================
echo.
echo CDP Proxy:  Running on 0.0.0.0:9224 ^(forwarding to 127.0.0.1:9222^)
echo Browser:    Running on 127.0.0.1:9222
echo.
echo Next steps:
echo   1. Open WSL terminal
echo   2. cd ~/mcp_comet_for_claude_code
echo   3. python3 server.py
echo.
echo To verify proxy is working from WSL:
echo   curl http://^$(cat /etc/resolv.conf ^| grep nameserver ^| awk '{print $2}'^):9224/json/version
echo.
echo Press any key to exit this window...
pause >nul
