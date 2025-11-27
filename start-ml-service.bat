@echo off
echo ========================================
echo E-Commerce Recommendation System Setup
echo ========================================
echo.

echo [1/5] Setting up database...
echo NOTE: Make sure PostgreSQL is running before continuing!
echo.
pause

REM Create database
echo Creating database...
psql -U postgres -c "DROP DATABASE IF EXISTS ecommerce;" 2>nul
psql -U postgres -c "CREATE DATABASE ecommerce;"
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to create database!
    echo Make sure PostgreSQL is running and accessible.
    echo Try: psql -U postgres
    pause
    exit /b 1
)

REM Load schema
echo Loading schema...
psql -U postgres -d ecommerce -f database\schema.sql
if %errorlevel% neq 0 (
    echo ERROR: Failed to load schema!
    pause
    exit /b 1
)
echo Database setup complete!

REM Generate sample data
echo.
echo [2/5] Generating sample data...
cd database\seeds
python generate_sample_data.py
if %errorlevel% neq 0 (
    echo ERROR: Failed to generate sample data!
    echo Make sure Python is installed and in PATH.
    cd ..\..
    pause
    exit /b 1
)
cd ..\..
echo Sample data generated!

REM Setup Python virtual environment
echo.
echo [3/5] Setting up Python environment...
cd ml-service

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment!
        echo Make sure Python 3.10+ is installed.
        cd ..
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [4/5] Installing dependencies...
pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python dependencies!
    cd ..
    pause
    exit /b 1
)
echo Dependencies installed!

REM Create .env file
echo.
echo [5/5] Creating configuration...
(
echo DB_HOST=localhost
echo DB_NAME=ecommerce
echo DB_USER=postgres
echo DB_PASSWORD=postgres
echo DB_PORT=5432
) > .env
echo Configuration created!

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo ML Service starting on http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the service
echo ========================================
echo.

uvicorn app.main:app --reload --port 8000
