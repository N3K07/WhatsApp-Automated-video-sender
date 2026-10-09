@echo off
setlocal
set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "PROFILE=%~dp0ChromeProfile"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" (
    echo Chrome was not found. Install Google Chrome or update the path in this file.
    pause
    exit /b 1
)
if not exist "%PROFILE%" mkdir "%PROFILE%"
echo Starting Chrome with remote debugging on port 9222...
start "WhatsApp Chrome" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%" --no-first-run --no-default-browser-check "https://web.whatsapp.com/"
endlocal
