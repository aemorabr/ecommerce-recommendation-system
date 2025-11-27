# Setup Guide

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (20.10+) and **Docker Compose** (2.0+)
- **Python** (3.10+)
- **Node.js** (18+) and **npm** (9+)
- **PostgreSQL** (15+)
- **Git**

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ecommerce-recommendation-system.git
cd ecommerce-recommendation-system
```

### 2. Environment Setup

#### ML Service
```bash
cd ml-service
cp .env.example .env
# Edit .env with your database credentials
```

#### Backend
```bash
cd backend-nodejs
cp .env.example .env
# Edit .env with your configuration
```

#### Frontend
```bash
cd frontend
cp .env.example .env.local
# Edit .env.local with your API URL
```

### 3. Database Setup

#### Option A: Using Docker Compose (Recommended)
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Wait for database to be ready
docker-compose exec postgres pg_isready

# Run schema
docker-compose exec postgres psql -U postgres -d ecommerce -f /docker-entrypoint-initdb.d/01-schema.sql
```

#### Option B: Local PostgreSQL
```bash
# Create database
createdb ecommerce

# Run schema
psql -U postgres -d ecommerce -f database/schema.sql

# Install pgvector extension
psql -U postgres -d ecommerce -c "CREATE EXTENSION vector;"
```

### 4. Generate Sample Data

```bash
cd database/seeds
pip install psycopg2-binary faker python-dotenv
python generate_sample_data.py
```

This will create:
- 100 products across 5 categories
- 500 customers
- ~2,500 purchase transactions

### 5. Start Services

#### Option A: Docker Compose (All Services)
```bash
docker-compose up -d
```

#### Option B: Local Development

**Terminal 1 - ML Service:**
```bash
cd ml-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Backend:**
```bash
cd backend-nodejs
npm install
npm run dev
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### 6. Verify Installation

Open your browser and check:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **ML Service Docs**: http://localhost:8000/docs
- **Health Checks**:
  ```bash
  curl http://localhost:8000/health
  curl http://localhost:5000/health
  ```

## Testing

### ML Service Tests
```bash
cd ml-service
pytest tests/ -v --cov=app
```

### Backend Tests
```bash
cd backend-nodejs
npm test
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Common Issues

### Issue: Database connection failed
**Solution:**
- Check PostgreSQL is running: `docker-compose ps`
- Verify credentials in `.env` files
- Ensure database exists: `psql -U postgres -l`

### Issue: ML service fails to start
**Solution:**
- Check Python version: `python --version` (should be 3.10+)
- Install dependencies: `pip install -r requirements.txt`
- Check database has data: `psql -U postgres -d ecommerce -c "SELECT COUNT(*) FROM purchases;"`

### Issue: Frontend can't connect to backend
**Solution:**
- Verify backend is running: `curl http://localhost:5000/health`
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- Check CORS settings in backend

### Issue: No recommendations returned
**Solution:**
- Ensure sample data is loaded
- Check ML service logs: `docker-compose logs ml-service`
- Manually trigger model training: `curl -X POST http://localhost:8000/retrain`

## Development Workflow

### Making Changes

1. **ML Model Changes**
   - Edit `ml-service/app/services/recommendation_engine.py`
   - Restart ML service
   - Test: `curl http://localhost:8000/recommendations/1`

2. **Backend API Changes**
   - Edit files in `backend-nodejs/`
   - Service auto-reloads with nodemon
   - Test: `curl http://localhost:5000/api/products`

3. **Frontend Changes**
   - Edit files in `frontend/src/`
   - Next.js auto-reloads
   - View: http://localhost:3000

### Adding New Features

1. Create a new branch: `git checkout -b feature/my-feature`
2. Make changes
3. Test locally
4. Commit: `git commit -m "Add my feature"`
5. Push: `git push origin feature/my-feature`
6. Create Pull Request

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions for:
- Render.com (Free tier)
- AWS (ECS, RDS, S3)
- Azure (Container Instances, PostgreSQL, Static Web Apps)

## Monitoring

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f ml-service

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Metrics
```bash
# Model metrics
curl http://localhost:8000/metrics

# Database stats
psql -U postgres -d ecommerce -c "SELECT * FROM customer_analytics LIMIT 5;"
```

## Maintenance

### Backup Database
```bash
docker-compose exec postgres pg_dump -U postgres ecommerce > backup.sql
```

### Restore Database
```bash
docker-compose exec -T postgres psql -U postgres ecommerce < backup.sql
```

### Update Dependencies
```bash
# ML Service
cd ml-service
pip install --upgrade -r requirements.txt

# Backend
cd backend-nodejs
npm update

# Frontend
cd frontend
npm update
```

## Getting Help

- Check [API Documentation](docs/API.md)
- Review [ML Model Details](docs/ML_MODEL.md)
- Open an issue on GitHub
- Contact: allanmb@me.com
