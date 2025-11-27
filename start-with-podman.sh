#!/bin/bash

echo "========================================"
echo "E-Commerce Recommendation System Setup"
echo "With Podman PostgreSQL Container"
echo "========================================"
echo ""

# Check if Podman is installed
echo "[1/6] Checking Podman..."
if ! command -v podman &> /dev/null; then
    echo "ERROR: Podman is not installed!"
    echo "Install Podman:"
    echo "  Mac: brew install podman"
    echo "  Linux: sudo apt install podman (or yum/dnf)"
    exit 1
fi
echo "✓ Podman is installed!"

# Stop and remove existing PostgreSQL container if it exists
echo ""
echo "[2/6] Setting up PostgreSQL container..."
podman stop ecommerce-postgres 2>/dev/null
podman rm ecommerce-postgres 2>/dev/null

# Start PostgreSQL container
echo "Starting PostgreSQL container..."
podman run -d \
  --name ecommerce-postgres \
  -e POSTGRES_DB=ecommerce \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15-alpine

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start PostgreSQL container!"
    exit 1
fi

echo "Waiting for PostgreSQL to be ready (15 seconds)..."
sleep 15

# Test PostgreSQL connection
echo "Testing PostgreSQL connection..."
podman exec ecommerce-postgres pg_isready -U postgres > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "WARNING: PostgreSQL might not be ready yet. Waiting 10 more seconds..."
    sleep 10
fi
echo "✓ PostgreSQL is ready!"

# Load schema into container
echo ""
echo "[3/6] Loading database schema..."
podman exec -i ecommerce-postgres psql -U postgres -d ecommerce < database/schema.sql
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to load schema!"
    exit 1
fi
echo "✓ Schema loaded successfully!"

# Generate sample data
echo ""
echo "[4/6] Generating sample data..."
cd database/seeds
python3 generate_sample_data.py
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to generate sample data!"
    cd ../..
    exit 1
fi
cd ../..
echo "✓ Sample data generated!"

# Setup Python virtual environment
echo ""
echo "[5/6] Setting up Python environment..."
cd ml-service

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment!"
        cd ..
        exit 1
    fi
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
echo "✓ Dependencies installed!"

# Create .env file
echo ""
echo "[6/6] Creating configuration..."
cat > .env << EOF
DB_HOST=localhost
DB_NAME=ecommerce
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432
EOF
echo "✓ Configuration created!"

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "PostgreSQL Container: ecommerce-postgres (running on port 5432)"
echo "ML Service starting on: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""
echo "To stop PostgreSQL later: podman stop ecommerce-postgres"
echo "To start PostgreSQL again: podman start ecommerce-postgres"
echo ""
echo "Press Ctrl+C to stop the ML service"
echo "========================================"
echo ""

uvicorn app.main:app --reload --port 8000
