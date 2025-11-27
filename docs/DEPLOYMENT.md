# Deployment Guide

## Local Development

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+
- PostgreSQL 15+

### Quick Start with Docker Compose

1. **Clone the repository**
```bash
git clone <your-repo>
cd ecommerce-recommendation-system
```

2. **Start all services**
```bash
docker-compose up -d
```

3. **Generate sample data**
```bash
docker-compose exec ml-service python /app/database/seeds/generate_sample_data.py
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- ML Service: http://localhost:8000/docs

---

## Deploy to Render.com (Free Tier)

### 1. Database (PostgreSQL)

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "PostgreSQL"
3. Configure:
   - Name: `ecommerce-db`
   - Database: `ecommerce`
   - User: `postgres`
   - Region: Choose closest
   - Plan: Free
4. Click "Create Database"
5. Note the connection details

### 2. ML Service

1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - Name: `ecommerce-ml-service`
   - Root Directory: `ml-service`
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `DB_HOST`: (from database connection)
   - `DB_NAME`: `ecommerce`
   - `DB_USER`: (from database)
   - `DB_PASSWORD`: (from database)
   - `DB_PORT`: `5432`
5. Click "Create Web Service"

### 3. Backend API

1. Click "New +" → "Web Service"
2. Configure:
   - Name: `ecommerce-backend`
   - Root Directory: `backend-nodejs`
   - Environment: Node
   - Build Command: `npm install`
   - Start Command: `npm start`
3. Add environment variables:
   - `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
   - `ML_SERVICE_URL`: (URL from ML service)
4. Click "Create Web Service"

### 4. Frontend

1. Click "New +" → "Static Site"
2. Configure:
   - Name: `ecommerce-frontend`
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `.next`
3. Add environment variable:
   - `NEXT_PUBLIC_API_URL`: (URL from backend)
4. Click "Create Static Site"

### 5. Initialize Database

```bash
# Connect to your Render PostgreSQL
psql <your-render-db-url>

# Run schema
\i database/schema.sql

# Exit psql
\q

# Generate sample data (update connection in script)
python database/seeds/generate_sample_data.py
```

---

## Deploy to AWS

### Architecture
- **ECS Fargate**: ML Service, Backend
- **S3 + CloudFront**: Frontend
- **RDS PostgreSQL**: Database
- **Application Load Balancer**: Traffic routing

### Steps

1. **Create RDS PostgreSQL Instance**
```bash
aws rds create-db-instance \
  --db-instance-identifier ecommerce-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password <password> \
  --allocated-storage 20
```

2. **Build and Push Docker Images**
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push ML service
docker build -t ecommerce-ml-service ./ml-service
docker tag ecommerce-ml-service:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/ecommerce-ml-service:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/ecommerce-ml-service:latest

# Repeat for backend
```

3. **Create ECS Task Definitions and Services**
Use the AWS Console or CloudFormation templates in `infrastructure/aws/`

4. **Deploy Frontend to S3**
```bash
cd frontend
npm run build
aws s3 sync out/ s3://ecommerce-frontend-bucket
```

5. **Configure CloudFront**
Create a CloudFront distribution pointing to your S3 bucket.

---

## Deploy to Azure

### Architecture
- **Azure Container Instances**: ML Service, Backend
- **Azure Static Web Apps**: Frontend
- **Azure Database for PostgreSQL**: Database

### Steps

1. **Create Resource Group**
```bash
az group create --name ecommerce-rg --location eastus
```

2. **Create PostgreSQL Database**
```bash
az postgres flexible-server create \
  --resource-group ecommerce-rg \
  --name ecommerce-db \
  --location eastus \
  --admin-user postgres \
  --admin-password <password> \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32
```

3. **Deploy Containers**
```bash
# ML Service
az container create \
  --resource-group ecommerce-rg \
  --name ml-service \
  --image <your-acr>.azurecr.io/ml-service:latest \
  --dns-name-label ecommerce-ml \
  --ports 8000 \
  --environment-variables DB_HOST=<db-host> DB_NAME=ecommerce

# Backend
az container create \
  --resource-group ecommerce-rg \
  --name backend \
  --image <your-acr>.azurecr.io/backend:latest \
  --dns-name-label ecommerce-api \
  --ports 5000
```

4. **Deploy Frontend**
```bash
cd frontend
az staticwebapp create \
  --name ecommerce-frontend \
  --resource-group ecommerce-rg \
  --source . \
  --location eastus \
  --branch main \
  --app-location "/" \
  --output-location ".next"
```

---

## Environment Variables Reference

### ML Service
- `DB_HOST`: Database host
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `DB_PORT`: Database port (default: 5432)
- `CORS_ORIGINS`: Allowed CORS origins

### Backend
- `PORT`: Server port (default: 5000)
- `NODE_ENV`: Environment (development/production)
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`
- `ML_SERVICE_URL`: ML service URL

### Frontend
- `NEXT_PUBLIC_API_URL`: Backend API URL

---

## Monitoring & Maintenance

### Health Checks
- ML Service: `GET /health`
- Backend: `GET /health`

### Model Retraining
Trigger manually or via cron:
```bash
curl -X POST http://your-ml-service/retrain
```

### Logs
```bash
# Docker Compose
docker-compose logs -f ml-service

# Render
View logs in dashboard

# AWS
aws logs tail /ecs/ml-service --follow

# Azure
az container logs --resource-group ecommerce-rg --name ml-service --follow
```
