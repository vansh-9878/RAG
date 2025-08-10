#!/bin/bash

# RAG Application Startup Script

echo "🤖 Starting RAG Document Query System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << EOF
# Authentication token for API access
TOKEN=your_secret_token_here

# Add other environment variables as needed
# GOOGLE_API_KEY=your_google_api_key
# PINECONE_API_KEY=your_pinecone_api_key
EOF
    echo "📝 Please edit .env file with your actual tokens before running the application"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the application
echo "🚀 Starting FastAPI server..."
echo "Frontend will be available at: http://localhost:8000"
echo "API documentation at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
