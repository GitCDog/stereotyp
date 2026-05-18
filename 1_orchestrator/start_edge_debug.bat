@echo off
echo Schliesse alle Edge-Fenster...
taskkill /F /IM msedge.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo Starte Edge mit Remote-Debugging auf Port 9222...
start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" ^
  --remote-debugging-port=9222 ^
  --profile-directory=Default ^
  --no-first-run ^
  "https://chatgpt.com/c/6a083e90-3238-83eb-ae9d-255dabbe121c"

echo.
echo Edge gestartet. Warte kurz damit der Browser laedt...
timeout /t 3 /nobreak >nul
echo Fertig! Jetzt kannst du das Script starten:
echo   python generate_pictures_playwright.py --story 49
echo.
pause
