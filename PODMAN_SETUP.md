# 🚀 Quick Start with Podman

## Step-by-Step Setup

### Step 1: Start PostgreSQL Container

```bash
podman run -d \
  --name ecommerce-postgres \
  -e POSTGRES_DB=ecommerce \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15-alpine
```

Wait 10 seconds for PostgreSQL to start, then verify:
```bash
podman ps
```

### Step 2: Load Database Schema

```bash
podman exec -i ecommerce-postgres psql -U postgres -d ecommerce < database/schema.sql
```

### Step 3: Generate Sample Data

```bash
cd database/seeds
python generate_sample_data.py
cd ../..
```

### Step 4: Setup ML Service

```bash
cd ml-service

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Windows CMD)
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Create .env file
@"
DB_HOST=localhost
DB_NAME=ecommerce
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432
"@ | Out-File -FilePath .env -Encoding utf8
```

### Step 5: Start ML Service

```bash
uvicorn app.main:app --reload --port 8000
```

### Step 6: Test the API

Open a new terminal:

```bash
# Health check
curl http://localhost:8000/health

# Get recommendations
curl "http://localhost:8000/recommendations/1?strategy=hybrid&limit=5"
```

Or visit: **http://localhost:8000/docs**

---

## Managing PostgreSQL Container

```bash
# Stop container
podman stop ecommerce-postgres

# Start container
podman start ecommerce-postgres

# View logs
podman logs ecommerce-postgres

# Connect to PostgreSQL
podman exec -it ecommerce-postgres psql -U postgres -d ecommerce

# Remove container
podman stop ecommerce-postgres
podman rm ecommerce-postgres
```

---

## Troubleshooting

### Container won't start
```bash
# Check if port 5432 is in use
netstat -an | findstr :5432

# Remove old container
podman rm -f ecommerce-postgres
```

### Can't connect to database
```bash
# Check container is running
podman ps

# Check PostgreSQL logs
podman logs ecommerce-postgres

# Test connection
podman exec ecommerce-postgres pg_isready -U postgres
```

### Python errors
```bash
# Make sure you're in virtual environment
# You should see (venv) in your prompt

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

---

## Quick Commands Reference

```bash
# Start everything
podman start ecommerce-postgres
cd ml-service
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Stop everything
# Press Ctrl+C in ML service terminal
podman stop ecommerce-postgres

# Reset database
podman exec -i ecommerce-postgres psql -U postgres -c "DROP DATABASE ecommerce;"
podman exec -i ecommerce-postgres psql -U postgres -c "CREATE DATABASE ecommerce;"
podman exec -i ecommerce-postgres psql -U postgres -d ecommerce < database/schema.sql
cd database/seeds && python generate_sample_data.py && cd ../..
```
