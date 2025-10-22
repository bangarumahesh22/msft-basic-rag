@echo off
REM Quick start script for the Azure RAG system (Windows)

echo ===================================
echo Azure RAG System - Quick Start
echo ===================================
echo.

REM Check if .env file exists
if not exist .env (
    echo Warning: .env file not found!
    echo Copying .env.example to .env...
    copy .env.example .env
    echo Created .env file. Please edit it with your Azure credentials before continuing.
    echo.
    echo Required configuration:
    echo   - AZURE_SEARCH_ENDPOINT
    echo   - AZURE_SEARCH_KEY
    echo   - AZURE_OPENAI_ENDPOINT
    echo   - AZURE_OPENAI_KEY
    echo   - AZURE_OPENAI_DEPLOYMENT_NAME
    echo.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo Installing dependencies...
pip install -q -r requirements.txt
echo Dependencies installed
echo.

REM Ask user what they want to do
echo What would you like to do?
echo 1) Ingest data into Azure AI Search
echo 2) Start the backend server
echo 3) Start the frontend application
echo 4) Run ingestion only, then exit
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    echo.
    echo Starting data ingestion...
    python src\ingestion\ingest.py
) else if "%choice%"=="2" (
    echo.
    echo Starting backend server...
    echo API will be available at http://localhost:8000
    echo API docs available at http://localhost:8000/docs
    python src\BE\main.py
) else if "%choice%"=="3" (
    echo.
    echo Starting frontend application...
    echo UI will be available at http://localhost:8501
    streamlit run src\FE\app.py
) else if "%choice%"=="4" (
    echo.
    echo Running data ingestion...
    python src\ingestion\ingest.py
    echo.
    echo Ingestion complete. 
    echo To start the system:
    echo   - Run backend: python src\BE\main.py
    echo   - Run frontend: streamlit run src\FE\app.py
    pause
) else (
    echo Invalid choice. Exiting.
    exit /b 1
)
