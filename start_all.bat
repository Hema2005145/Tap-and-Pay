@echo off
color 0A
echo ==========================================================
echo        QSP3 PAYMENT SYSTEM - 1-CLICK STARTUP
echo ==========================================================
echo.
echo Initializing Microservices Architecture...
echo.

echo [1/3] Starting Python Cloud Backend (FastAPI)...
start "QSP3 - FastAPI Backend" cmd /c "cd server && ..\.venv\Scripts\python.exe -m uvicorn api_gateway:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 2 >nul

echo [2/3] Starting Node.js WebSocket Relay Server...
start "QSP3 - WebSocket Server" cmd /c "cd mobile_ui && node server.cjs"
timeout /t 1 >nul

echo [3/3] Starting React Edge UI (Vite)...
start "QSP3 - React UI" cmd /c "cd mobile_ui && npm run dev -- --host"

echo.
echo ==========================================================
echo ALL SYSTEMS ONLINE!
echo ==========================================================
echo The Cloud Backend, WebSocket Relay, and UI are running
echo in separate background terminal windows.
echo.
echo You can now open Chrome on your phone and navigate to:
echo http://192.168.0.4:5173
echo.
pause
