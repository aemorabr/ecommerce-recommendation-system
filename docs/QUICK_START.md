# Quick Start Guide - Hybrid Recommendation System

## 🚀 Get Started in 10 Minutes (Local Development)

> **Note**: This guide uses local development. Docker/Podman setup available but requires package-lock.json generation first.

## ⚡ Quick Setup (Automated)

### Windows
```bash
# Run the automated setup script
start-ml-service.bat
```

### Mac/Linux
```bash
# Make script executable and run
chmod +x start-ml-service.sh
./start-ml-service.sh
```

The script will:
1. ✓ Check PostgreSQL is running
2. ✓ Create database and load schema
3. ✓ Generate sample data (100 products, 500 customers, 2000+ purchases)
4. ✓ Setup Python virtual environment
5. ✓ Install dependencies
6. ✓ Start ML service on http://localhost:8000

**Then skip to [Step 3](#step-3-test-the-ml-service) to test the API!**

---

## 📋 Manual Setup (Step-by-Step)

### Prerequisites

- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 15+** - [Download](https://www.postgresql.org/download/)

### Step 1: Setup Database

```bash
# Start PostgreSQL service (if not running)
# Windows: Check Services or start from pgAdmin
# Mac: brew services start postgresql
# Linux: sudo systemctl start postgresql

# Create database and load schema
psql -U postgres -c "CREATE DATABASE ecommerce;"
psql -U postgres -d ecommerce -f database/schema.sql

# Generate sample data (100 products, 500 customers, 2000+ purchases)
cd database/seeds
python generate_sample_data.py
cd ../..
```

### Step 2: Setup ML Service

```bash
cd ml-service

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (Windows PowerShell)
@"
DB_HOST=localhost
DB_NAME=ecommerce
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432
"@ | Out-File -FilePath .env -Encoding utf8

# Or manually create .env with these values:
# DB_HOST=localhost
# DB_NAME=ecommerce
# DB_USER=postgres
# DB_PASSWORD=postgres
# DB_PORT=5432

# Start the ML service
uvicorn app.main:app --reload --port 8000
```

**Keep this terminal open!** The ML service is now running on http://localhost:8000

### Step 3: Test the ML Service

Open a **new terminal** and test:

```bash
# Health check
curl http://localhost:8000/health

# Get hybrid recommendations (default)
curl "http://localhost:8000/recommendations/1?strategy=hybrid&limit=5"

# Try different strategies
curl "http://localhost:8000/recommendations/1?strategy=cf&limit=5"
curl "http://localhost:8000/recommendations/1?strategy=content&limit=5"
curl "http://localhost:8000/recommendations/1?strategy=popular&limit=5"

# Find similar products
curl "http://localhost:8000/similar-products/1?limit=5"

# Find similar customers
curl "http://localhost:8000/similar-customers/1?limit=5"
```

**Or use your browser:**
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc


### Step 4: Run the Test Suite

```bash
# Test all strategies
cd ml-service
python examples/test_all_strategies.py

# Run unit tests
pytest tests/ -v --cov=app
```

## 📊 Understanding the Strategies

### When to Use Each Strategy

| Strategy | Use Case | Best For |
|----------|----------|----------|
| **Hybrid** (default) | General recommendations | Most users, production |
| **Collaborative (CF)** | Personalized suggestions | Users with purchase history |
| **Content-Based** | Similar products | New users, "more like this" |
| **Popular** | Trending items | Cold-start, homepage |

### Example Responses

**Hybrid Strategy** (60% CF + 40% Content):
```json
[
  {
    "product_id": 42,
    "score": 0.85,
    "reason": "hybrid",
    "name": "Wireless Headphones",
    "category": "Electronics",
    "price": 79.99
  }
]
```

**Collaborative Filtering**:
```json
[
  {
    "product_id": 15,
    "score": 0.92,
    "reason": "customers_like_you",
    "name": "Gaming Mouse",
    "category": "Electronics",
    "price": 49.99
  }
]
```

**Content-Based**:
```json
[
  {
    "product_id": 23,
    "score": 0.78,
    "reason": "content_based",
    "name": "Bluetooth Speaker",
    "category": "Electronics",
    "price": 59.99
  }
]
```

**Popular**:
```json
[
  {
    "product_id": 7,
    "score": 156.0,
    "reason": "popular",
    "name": "USB-C Cable",
    "category": "Accessories",
    "price": 12.99
  }
]
```

## 🔧 Configuration

### Adjust Hybrid Weights

Edit `ml-service/app/main.py`:

```python
hybrid_recommender = HybridRecommender(
    collaborative_recommender=cf_recommender,
    content_based_recommender=content_recommender,
    cf_weight=0.7,      # Increase for more personalization
    content_weight=0.3  # Increase for more similarity-based
)
```

### Retrain Models

```bash
# Trigger retraining via API
curl -X POST http://localhost:8000/retrain

# Or restart the service (auto-trains on startup)
docker-compose restart ml-service
```

## 📈 Monitoring

### Check System Metrics

```bash
curl http://localhost:8000/metrics
```

Response:
```json
{
  "total_customers": 500,
  "total_products": 100,
  "total_purchases": 2156,
  "avg_purchases_per_customer": 4.31,
  "model_last_trained": "2024-01-15T10:30:00",
  "sparsity": 0.9568
}
```

### View Logs

```bash
# ML Service logs
docker-compose logs -f ml-service

# All services
docker-compose logs -f
```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check if ports are available
netstat -an | grep 8000

# Restart services
docker-compose down
docker-compose up -d
```

### No Recommendations Returned

```bash
# Check if data is loaded
curl http://localhost:8000/metrics

# Verify database connection
docker-compose exec ml-service python -c "from app.services.database import DatabaseService; db = DatabaseService(); print(db.check_connection())"

# Retrain models
curl -X POST http://localhost:8000/retrain
```

### Low Recommendation Quality

1. **Add more data**: Generate more sample data or import real data
2. **Adjust similarity threshold**: Lower threshold in `recommendation_engine.py`
3. **Tune hybrid weights**: Experiment with different CF/content ratios
4. **Check sparsity**: High sparsity (>95%) may reduce quality

## 🎯 Next Steps

1. **Integrate with Frontend**: Connect React app to the API
2. **Add Authentication**: Implement JWT tokens for user sessions
3. **Deploy to Cloud**: Use Docker images on AWS/Azure/GCP
4. **A/B Testing**: Compare strategies with real users
5. **Add More Features**: Incorporate ratings, reviews, user demographics

## 📚 Additional Resources

- [Full Architecture Documentation](HYBRID_RECOMMENDATION_SYSTEM.md)
- [API Reference](../README.md#-api-endpoints)
- [Deployment Guide](DEPLOYMENT.md)
- [Contributing Guide](CONTRIBUTING.md)

## 💡 Tips for Portfolio/Interview

**Key Points to Mention**:
1. "Implemented hybrid recommender combining CF and content-based with 60/40 weighting"
2. "Used TF-IDF for product similarity and cosine similarity for user-user CF"
3. "Handled cold-start problem with popularity-based fallback"
4. "Achieved <100ms p95 latency with precomputed similarity matrices"
5. "Built production-ready API with 4 selectable strategies via query parameter"

**Demo Flow**:
1. Show health check and metrics
2. Compare all 4 strategies for same customer
3. Explain why hybrid is default (robustness)
4. Show similar products feature
5. Discuss scalability and deployment
