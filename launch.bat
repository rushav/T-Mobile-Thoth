@echo off
echo Starting Project Thoth...

REM Backend
start "Thoth Backend" cmd /c "cd backend && pip install -r requirements.txt -q && python seed.py 2>nul && uvicorn main:app --reload --port 8000"

echo Waiting for backend...
timeout /t 8 /nobreak >nul

REM Frontend
start "Thoth Frontend" cmd /c "cd frontend && npm install -q && npm run dev"

echo Waiting for frontend...
timeout /t 8 /nobreak >nul

REM Open one browser tab
start http://localhost:5173

echo.
echo Project Thoth is running!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo.
pause
