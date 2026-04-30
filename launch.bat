@echo off
echo Starting Project Thoth...

REM Start backend
start "Thoth Backend" cmd /c "cd backend && pip install -r requirements.txt -q && python seed.py 2>nul && uvicorn main:app --reload --port 8000"

REM Wait for backend
echo Waiting for backend...
timeout /t 8 /nobreak >nul

REM Start frontend
start "Thoth Frontend" cmd /c "cd frontend && npm install -q && npm run dev"

REM Wait for frontend
echo Waiting for frontend...
timeout /t 8 /nobreak >nul

REM Open 4 Chrome windows in grid
start chrome --new-window --window-size=960,540 --window-position=0,0 "http://localhost:5173/user"
timeout /t 1 /nobreak >nul
start chrome --new-window --window-size=960,540 --window-position=960,0 "http://localhost:5173/sme"
timeout /t 1 /nobreak >nul
start chrome --new-window --window-size=960,540 --window-position=0,540 "http://localhost:5173/admin"
timeout /t 1 /nobreak >nul
start chrome --new-window --window-size=960,540 --window-position=960,540 "http://localhost:5173/support"

echo.
echo Project Thoth is running!
echo   Top-left: USER    Top-right: SME
echo   Bot-left: ADMIN   Bot-right: SUPPORT
echo.
pause
