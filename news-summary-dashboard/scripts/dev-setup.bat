@echo off
REM Development setup script for Windows

echo 🔧 Setting up development environment...

REM Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed. Please install Node.js first.
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python first.
    exit /b 1
)

REM Setup backend
echo 📦 Setting up backend...
cd backend
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python packages...
pip install -r requirements.txt

cd ..

REM Setup frontend
echo 🎨 Setting up frontend...
cd frontend

echo Installing Node packages...
npm install

cd ..

echo ✅ Development environment setup complete!
echo.
echo 🚀 To start development:
echo 1. Backend: cd backend && venv\Scripts\activate && python run.py
echo 2. Frontend: cd frontend && npm start
echo.

pause
