@echo off
echo 🏥 PrescriptionReader Setup Script
echo ==================================

REM Check if we're in the right directory
if not exist "docker-compose.yml" (
    echo ❌ Please run this script from the prescription-reader root directory
    pause
    exit /b 1
)

echo 📦 Installing backend dependencies...
cd backend
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..

echo 📦 Installing frontend dependencies...
cd frontend
npm install
cd ..

echo ⚙️  Setting up environment...
if not exist "backend\.env" (
    copy "backend\.env.example" "backend\.env"
    echo 📝 Created backend\.env - please add your GROQ_API_KEY
)

echo 🧪 Running setup verification...
python test_setup.py

echo.
echo ✅ Setup complete!
echo.
echo Next steps:
echo 1. Add your GROQ_API_KEY to backend\.env
echo 2. Run: docker-compose up --build
echo 3. Open: http://localhost:3000
pause