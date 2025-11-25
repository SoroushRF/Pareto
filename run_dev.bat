@echo off
cd /d "%~dp0"

echo Starting Backend...
start "Pareto Backend" cmd /k "cd backend && uvicorn main:app --reload --port 8000"

echo Starting Frontend...
start "Pareto Frontend" cmd /k "cd frontend && npm run dev"

echo Both servers are starting in new windows!
