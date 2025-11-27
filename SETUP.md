# Local Development Setup

## 🐳 Podman Setup (Recommended for Your Environment)

Since you're using Podman, this is the easiest way to get started!

### Quick Start with Podman

**Windows:**
```bash
start-with-podman.bat
```

**Mac/Linux:**
```bash
chmod +x start-with-podman.sh
./start-with-podman.sh
```

This automated script will:
1. ✓ Start PostgreSQL in a Podman container
2. ✓ Create database and load schema
3. ✓ Generate sample data (100 products, 500 customers, 2000+ purchases)
4. ✓ Setup Python virtual environment
5. ✓ Install dependencies
6. ✓ Start ML service on http://localhost:8000

### Managing PostgreSQL Container

Use the helper script to manage your PostgreSQL container:

```bash
# Start PostgreSQL
postgres-podman.bat start

# Stop PostgreSQL
postgres-podman.bat stop

# Check status
postgres-podman.bat status

# View logs
postgres-podman.bat logs

# Connect to PostgreSQL shell
postgres-podman.bat shell

# Restart container
postgres-podman.bat restart

# Remove container
postgres-podman.bat remove
```

---

## 📋 Prerequisites Check

Before running the setup script, ensure you have:

### 1. PostgreSQL Installed and Running

**Check if installed:**
```bash
psql --version
```

**Start PostgreSQL:**
- **Windows**: 
  - Open Services (Win+R → `services.msc`)
  - Find "postgresql-x64-15" and click Start
  - Or use pgAdmin and start the server
  
- **Mac**:
  ```bash
  brew services start postgresql
  ```
  
- **Linux**:
  ```bash
  sudo systemctl start postgresql
  ```

**Test connection:**
```bash
psql -U postgres
# Type \q to exit
```

### 2. Python 3.10+ Installed

**Check version:**
```bash
python --version
# or
python3 --version
```

**Download if needed:** https://www.python.org/downloads/

### 3. Git (Optional, for cloning)

```bash
git --version
```

---

## Quick Start

### Windows

1. Open PowerShell or Command Prompt
2. Navigate to project directory:
   ```bash
   cd C:\Projects\ecommerce-recommendation-system
   ```
3. Run the setup script:
   ```bash
   start-ml-service.bat
   ```

### Mac/Linux

1. Open Terminal
2. Navigate to project directory:
   ```bash
   cd ~/Projects/ecommerce-recommendation-system
   ```
3. Make script executable and run:
   ```bash
   chmod +x start-ml-service.sh
   ./start-ml-service.sh
   ```

---

## What the Script Does

The automated script performs these steps:

1. **Database Setup**
   - Creates `ecommerce` database
   - Loads schema from `database/schema.sql`
   - Creates tables: products, customers, purchases

2. **Sample Data Generation**
   - Generates 100 products across 5 categories
   - Creates 500 customers with realistic profiles
   - Generates 2000+ purchase transactions

3. **Python Environment**
   - Creates virtual environment in `ml-service/venv`
   - Installs all dependencies from `requirements.txt`
   - Creates `.env` configuration file

4. **ML Service Startup**
   - Trains recommendation models on startup
   - Starts FastAPI server on port 8000
   - Enables hot-reload for development

---

## Testing the API

Once the service is running, open a **new terminal** and test:

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Get recommendations (hybrid strategy - default)
curl "http://localhost:8000/recommendations/1?strategy=hybrid&limit=5"

# Try collaborative filtering
curl "http://localhost:8000/recommendations/1?strategy=cf&limit=5"

# Try content-based filtering
curl "http://localhost:8000/recommendations/1?strategy=content&limit=5"

# Get popular products
curl "http://localhost:8000/recommendations/1?strategy=popular&limit=5"

# Find similar products
curl "http://localhost:8000/similar-products/1?limit=5"
```

### Using Browser

- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

### Using Python Test Script

```bash
cd ml-service
python examples/test_all_strategies.py
```

---

## Troubleshooting

### PostgreSQL Connection Error

**Error**: `psql: error: connection to server failed`

**Solutions**:
1. Check if PostgreSQL is running (see Prerequisites)
2. Verify default user exists:
   ```bash
   psql -U postgres
   ```
3. If password is different, update `.env` file in `ml-service/`

### Python Not Found

**Error**: `'python' is not recognized`

**Solutions**:
1. Install Python 3.10+ from https://python.org
2. During installation, check "Add Python to PATH"
3. Try `python3` instead of `python`

### Port 8000 Already in Use

**Error**: `Address already in use`

**Solutions**:
1. Find and kill the process:
   ```bash
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   
   # Mac/Linux
   lsof -ti:8000 | xargs kill -9
   ```
2. Or use a different port:
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

### Virtual Environment Issues

**Error**: `venv\Scripts\activate : cannot be loaded`

**Solutions**:
1. **Windows PowerShell**: Run as Administrator and execute:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
2. **Windows CMD**: Use `venv\Scripts\activate.bat` instead
3. **Mac/Linux**: Use `source venv/bin/activate`

### No Recommendations Returned

**Issue**: API returns empty array `[]`

**Solutions**:
1. Check if data was loaded:
   ```bash
   curl http://localhost:8000/metrics
   ```
2. Verify database has data:
   ```bash
   psql -U postgres -d ecommerce -c "SELECT COUNT(*) FROM purchases;"
   ```
3. Retrain models:
   ```bash
   curl -X POST http://localhost:8000/retrain
   ```

---

## Manual Setup (Alternative)

If the automated script doesn't work, follow these manual steps:

### 1. Database Setup

```bash
# Create database
psql -U postgres -c "CREATE DATABASE ecommerce;"

# Load schema
psql -U postgres -d ecommerce -f database/schema.sql

# Generate data
cd database/seeds
python generate_sample_data.py
cd ../..
```

### 2. ML Service Setup

```bash
cd ml-service

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo DB_HOST=localhost > .env
echo DB_NAME=ecommerce >> .env
echo DB_USER=postgres >> .env
echo DB_PASSWORD=postgres >> .env
echo DB_PORT=5432 >> .env

# Start service
uvicorn app.main:app --reload --port 8000
```

---

## Next Steps

1. ✅ **Test all strategies** - Try CF, content-based, hybrid, and popular
2. ✅ **Explore API docs** - Visit http://localhost:8000/docs
3. ✅ **Run test suite** - `pytest tests/ -v`
4. ✅ **Check metrics** - Monitor system performance
5. ✅ **Read architecture docs** - See `docs/HYBRID_RECOMMENDATION_SYSTEM.md`

---

## Development Tips

### Hot Reload

The service runs with `--reload` flag, so code changes automatically restart the server.

### Debugging

Add breakpoints and run:
```bash
python -m debugpy --listen 5678 -m uvicorn app.main:app --reload
```

### Running Tests

```bash
cd ml-service
pytest tests/ -v --cov=app
```

### Viewing Logs

The service logs to console. For production, configure logging in `app/main.py`.

---

## Docker/Podman Setup (Advanced)

If you prefer containers, first generate `package-lock.json`:

```bash
cd backend-nodejs
npm install
cd ..

# Then use Docker/Podman
docker-compose up -d
# or
podman-compose up -d
```

---

## Support

For issues or questions:
1. Check [QUICK_START.md](docs/QUICK_START.md)
2. Review [HYBRID_RECOMMENDATION_SYSTEM.md](docs/HYBRID_RECOMMENDATION_SYSTEM.md)
3. Open an issue on GitHub
