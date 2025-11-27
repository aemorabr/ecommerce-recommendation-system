#!/bin/bash

echo "========================================"
echo "E-Commerce Recommendation System Setup"
echo "========================================"
echo ""

# Check if PostgreSQL is running
echo "[1/5] Checking PostgreSQL..."
if ! pg_isready -U postgres > /dev/null 2>&1; then
    echo "ERROR: PostgreSQL is not running!"
    echo "Please start PostgreSQL and try again:"
    echo "  Mac: brew services start postgresql"
    echo "  Linux: sudo systemctl start postgresql"
    exit 1
fi
echo "✓ PostgreSQL is running!"

# Create database
echo ""
echo "[2/5] Setting up database..."
psql -U postgres -c "DROP DATABASE IF EXISTS ecommerce;" > /dev/null 2>&1
psql -U postgres -c "CREATE DATABASE ecommerce;"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create database!"
    exit 1
fi

# Load schema
echo "Loading schema..."
psql -U postgres -d ecommerce -f database/schema.sql
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to load schema!"
    exit 1
fi

# Generate sample data
echo ""
echo "[3/5] Generating sample data..."
cd database/seeds
python3 generate_sample_data.py
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to generate sample data!"
    cd ../..
    exit 1
fi
cd ../..

# Setup Python virtual environment
echo ""
echo "[4/5] Setting up Python environment..."
cd ml-service

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install Python dependencies!"
    cd ..
    exit 1
fi

# Create .env file
echo "Creating .env file..."
cat > .env << EOF
DB_HOST=localhost
DB_NAME=ecommerce
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432
EOF

echo ""
echo "[5/5] Starting ML Service..."
echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "ML Service starting on http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the service"
echo "========================================"
echo ""

uvicorn app.main:app --reload --port 8000
