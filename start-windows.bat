@echo off
echo Starting YT Transcriber...

echo Starting Backend...
start cmd /k "cd backend && python app.py"

echo Starting Frontend...
cd frontend
npm install
npm run start-win

pause
