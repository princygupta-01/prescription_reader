#!/bin/bash

echo "🏥 PrescriptionReader Setup Script"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the prescription-reader root directory"
    exit 1
fi

echo "📦 Installing backend dependencies..."
cd backend
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..

echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo "⚙️  Setting up environment..."
if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo "📝 Created backend/.env - please add your GROQ_API_KEY"
fi

echo "🧪 Running setup verification..."
python test_setup.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Add your GROQ_API_KEY to backend/.env"
echo "2. Run: docker-compose up --build"
echo "3. Open: http://localhost:3000"