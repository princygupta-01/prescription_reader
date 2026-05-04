@echo off
REM PrescriptionReader Development Startup Script for Windows

echo 🏥 Starting PrescriptionReader Development Environment
echo ==================================================

REM Check if we're in the right directory
if not exist "docker-compose.yml" (
    echo ❌ Please run this script from the prescription-reader root directory
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist "backend\.env" (
    echo ⚠️  Creating .env file from template...
    copy "backend\.env.example" "backend\.env"
    echo 📝 Please edit backend\.env and add your GROQ_API_KEY
    echo    You can get a free API key from: https://console.groq.com/
    pause
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo 🐳 Starting services with Docker Compose...
docker-compose up --build

echo 🎉 PrescriptionReader is now running!
echo 📱 Frontend: http://localhost:3000
echo 🔧 Backend API: http://localhost:8000
echo 📊 API Docs: http://localhost:8000/docs
pause