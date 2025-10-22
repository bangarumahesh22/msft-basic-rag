#!/bin/bash
# Quick start script for the Azure RAG system

echo "==================================="
echo "Azure RAG System - Quick Start"
echo "==================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "✓ Created .env file. Please edit it with your Azure credentials before continuing."
    echo ""
    echo "Required configuration:"
    echo "  - AZURE_SEARCH_ENDPOINT"
    echo "  - AZURE_SEARCH_KEY"
    echo "  - AZURE_OPENAI_ENDPOINT"
    echo "  - AZURE_OPENAI_KEY"
    echo "  - AZURE_OPENAI_DEPLOYMENT_NAME"
    echo ""
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    echo "✓ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Ask user what they want to do
echo "What would you like to do?"
echo "1) Ingest data into Azure AI Search"
echo "2) Start the backend server"
echo "3) Start the frontend application"
echo "4) Run ingestion, backend, and frontend (recommended)"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "Starting data ingestion..."
        python src/ingestion/ingest.py
        ;;
    2)
        echo ""
        echo "Starting backend server..."
        echo "API will be available at http://localhost:8000"
        echo "API docs available at http://localhost:8000/docs"
        python src/BE/main.py
        ;;
    3)
        echo ""
        echo "Starting frontend application..."
        echo "UI will be available at http://localhost:8501"
        streamlit run src/FE/app.py
        ;;
    4)
        echo ""
        echo "Running full setup..."
        echo ""
        
        # Step 1: Ingest data
        echo "Step 1/3: Ingesting data..."
        python src/ingestion/ingest.py
        
        # Step 2: Start backend in background
        echo ""
        echo "Step 2/3: Starting backend server..."
        python src/BE/main.py &
        BACKEND_PID=$!
        sleep 3
        
        # Step 3: Start frontend
        echo ""
        echo "Step 3/3: Starting frontend application..."
        echo ""
        echo "✓ Backend running at http://localhost:8000"
        echo "✓ Frontend will open at http://localhost:8501"
        echo ""
        streamlit run src/FE/app.py
        
        # Cleanup on exit
        echo ""
        echo "Stopping backend server..."
        kill $BACKEND_PID
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac
