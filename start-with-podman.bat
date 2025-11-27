@echo off
echo ========================================
echo E-Commerce Recommendation System Setup
echo With Podman PostgreSQL Container
echo ========================================
echo.

REM Check if Podman is installed
echo [1/6] Checking Podman...
podman --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Podman is not installed or not in PATH!
    echo Please install Podman Desktop from: https://podman.io/
    pause
    exit /b 1
)
echo Podman is installed!

REM Stop and remove existing PostgreSQL container if it exists
echo.
echo [2/6] Setting up PostgreSQL container...
podman stop ecommerce-postgres 2>nul
podman rm ecommerce-postgres 2>nul

REM Start PostgreSQL container
echo Starting PostgreSQL container...
podman run -d ^
  --name ecommerce-postgres ^
  -e POSTGRES_DB=ecommerce ^
  -e POSTGRES_USER=postgres ^
  -e POSTGRES_PASSWORD=postgres ^
  -p 5432:5432 ^
  postgres:15-alpine

if %errorlevel% neq 0 (
    echo ERROR: Failed to start PostgreSQL container!
    pause
    exit /b 1
)

echo Waiting for PostgreSQL to be ready (15 seconds)...
timeout /t 15 /nobreak >nul

REM Test PostgreSQL connection
echo Testing PostgreSQL connection...
podman exec ecommerce-postgres pg_isready -U postgres >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: PostgreSQL might not be ready yet. Waiting 10 more seconds...
    timeout /t 10 /nobreak >nul
)
echo PostgreSQL is ready!

REM Load schema into container
echo.
echo [3/6] Loading database schema...
podman exec -i ecommerce-postgres psql -U postgres -d ecommerce < database\schema.sql
if %errorlevel% neq 0 (
    echo ERROR: Failed to load schema!
    pause
    exit /b 1
)
echo Schema loaded successfully!

REM Generate sample data
echo.
echo [4/6] Generating sample data...
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
echo [5/6] Setting up Python environment...
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

echo Installing dependencies...
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
echo [6/6] Creating configuration...
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
echo PostgreSQL Container: ecommerce-postgres (running on port 5432)
echo ML Service starting on: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.
echo To stop PostgreSQL later: podman stop ecommerce-postgres
echo To start PostgreSQL again: podman start ecommerce-postgres
echo.
echo Press Ctrl+C to stop the ML service
echo ========================================
echo.

uvicorn app.main:app --reload --port 8000
