#!/bin/bash

# PrescriptionReader Development Startup Script

echo "🏥 Starting PrescriptionReader Development Environment"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the prescription-reader root directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f "backend/.env" ]; then
    echo "⚠️  Creating .env file from template..."
    cp backend/.env.example backend/.env
    echo "📝 Please edit backend/.env and add your GROQ_API_KEY"
    echo "   You can get a free API key from: https://console.groq.com/"
    read -p "Press Enter after adding your API key..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "🐳 Starting services with Docker Compose..."
docker-compose up --build

echo "🎉 PrescriptionReader is now running!"
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"