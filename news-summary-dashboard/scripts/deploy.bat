@echo off
REM Deploy script for Windows environment

echo 🚀 Starting deployment process...

REM Check if docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker first.
    exit /b 1
)

REM Check if docker-compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    exit /b 1
)

REM Check if required .env files exist
if not exist ".\backend\.env" (
    echo ❌ Backend .env file not found. Please create .\backend\.env
    exit /b 1
)

if not exist ".\frontend\.env" (
    echo ❌ Frontend .env file not found. Please create .\frontend\.env
    exit /b 1
)

REM Stop existing containers
echo 🛑 Stopping existing containers...
docker-compose down

REM Remove old images (optional)
echo 🗑️ Cleaning up old images...
docker system prune -f

REM Build and start new containers
echo 🔨 Building and starting containers...
docker-compose up --build -d

REM Wait for services to be ready
echo ⏳ Waiting for services to start...
timeout /t 30 /nobreak >nul

REM Check if services are running
echo 🔍 Checking service health...
curl -f http://localhost:5000/api/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Backend is healthy
) else (
    echo ❌ Backend health check failed
)

curl -f http://localhost:3000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Frontend is healthy
) else (
    echo ❌ Frontend health check failed
)

REM Show running containers
echo 📋 Running containers:
docker-compose ps

echo 🎉 Deployment complete!
echo 🌐 Frontend: http://localhost:3000
echo 🔧 Backend API: http://localhost:5000

pause
