# E-Commerce Recommendation System - ML Service

## Overview

This ML service provides AI-powered product recommendations using **pgvector-backed embeddings** stored in PostgreSQL. All recommendation strategies (collaborative filtering, content-based, and hybrid) leverage vector similarity search for fast and scalable recommendations.

## Architecture

The system uses **pgvector** extension for PostgreSQL to store and query embeddings:

- **Product Embeddings**: TF-IDF vectors (128-dim) from product text (name, category, description)
- **Customer Embeddings**: Normalized purchase pattern vectors representing customer preferences
- **ANN Search**: IVFFlat indexes for sub-100ms similarity queries

## Prerequisites

- PostgreSQL 12+ with **pgvector extension installed**
- Python 3.8+
- Database with `products`, `customers`, and `purchases` tables

## Quick Start

### 1. Install Dependencies

```bash
cd ml-service
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export DB_HOST=localhost
export DB_NAME=ecommerce
export DB_USER=postgres
export DB_PASSWORD=your_password
export DB_PORT=5432
```

Or create a `.env` file:
```env
DB_HOST=localhost
DB_NAME=ecommerce
DB_USER=postgres
DB_PASSWORD=your_password
DB_PORT=5432
```

### 3. Run Database Migration

```bash
# Connect to your database
export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

# Run the migration script
psql $DATABASE_URL -f ../database/migrations/00_add_vector_tables.sql
```

This creates:
- `model_versions` table (tracks model iterations)
- `product_embeddings` table (stores product vectors)
- `customer_embeddings` table (stores customer preference vectors)
- IVFFlat ANN indexes for fast similarity search

### 4. Start the Service

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The service will start but **requires training** before serving recommendations.

### 5. Train Models and Generate Embeddings

```bash
curl -X POST http://localhost:8000/retrain
```

This will:
1. Load purchase and product data
2. Compute TF-IDF product embeddings → store to `product_embeddings`
3. Compute customer purchase embeddings → store to `customer_embeddings`
4. Create a `model_version` record with metadata
5. Build ANN indexes for fast queries

Expected response:
```json
{
  "status": "success",
  "model_version_id": 1,
  "customers": 500,
  "products": 100,
  "product_embeddings": 95,
  "customer_embeddings": 450,
  "embedding_dimension": 128
}
```

### 6. Get Recommendations

```bash
# Hybrid recommendations (default)
curl "http://localhost:8000/recommendations/1?strategy=hybrid&limit=10"

# Collaborative filtering only
curl "http://localhost:8000/recommendations/1?strategy=cf&limit=10"

# Content-based only
curl "http://localhost:8000/recommendations/1?strategy=content&limit=10"

# Popular products
curl "http://localhost:8000/recommendations/1?strategy=popular&limit=10"
```

All strategies (except popular) now use **pgvector similarity search** under the hood.

## API Endpoints

### Core Endpoints

- `GET /` - API info and status
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

### Recommendation Endpoints

- `GET /recommendations/{customer_id}?strategy=hybrid&limit=5` - Get personalized recommendations
- `GET /similar-customers/{customer_id}?limit=5` - Find similar customers (pgvector-backed)
- `GET /similar-products/{product_id}?limit=5` - Find similar products (pgvector-backed)

### Model Management

- `POST /retrain` - Retrain models and regenerate all embeddings
- `GET /metrics` - Get model performance metrics

## How It Works

### Collaborative Filtering (CF)

1. User-item purchase matrix is computed
2. Customer vectors are normalized (L2 norm)
3. Customer embeddings stored to database
4. At recommendation time:
   - Query database for similar customers (pgvector ANN search)
   - Aggregate products purchased by similar customers
   - Rank by weighted scores
   - Exclude already-purchased items

### Content-Based Filtering

1. Product text (name + category + description) is vectorized using TF-IDF
2. Vectors are normalized (L2 norm)
3. Product embeddings stored to database
4. At recommendation time:
   - Get embeddings for customer's purchased products
   - For each purchased product, find similar products (pgvector ANN search)
   - Aggregate similarity scores
   - Return top-N recommendations

### Hybrid

Combines CF and Content-Based with weighted scores (60% CF + 40% Content).

## Database Schema

### model_versions
```sql
id               SERIAL PRIMARY KEY
name             TEXT
dimension        INT NOT NULL
params           JSONB
metrics          JSONB
created_at       TIMESTAMPTZ DEFAULT NOW()
```

### product_embeddings
```sql
product_id       BIGINT PRIMARY KEY
embedding        vector(128) NOT NULL
model_version_id INT REFERENCES model_versions(id)
created_at       TIMESTAMPTZ DEFAULT NOW()
```

### customer_embeddings
```sql
customer_id      BIGINT PRIMARY KEY
embedding        vector(128) NOT NULL
model_version_id INT REFERENCES model_versions(id)
updated_at       TIMESTAMPTZ DEFAULT NOW()
```

## Performance

- **Query Latency**: < 100ms for similarity search (with ANN indexes)
- **Scalability**: Handles 100k+ products and customers
- **Storage**: ~512 bytes per embedding (128 floats × 4 bytes)

## Configuration

### TF-IDF Parameters
Edit `app/services/content_based_recommender.py`:
```python
self.tfidf_vectorizer = TfidfVectorizer(
    max_features=500,  # Embedding dimension
    stop_words='english',
    ngram_range=(1, 2)
)
```

### IVFFlat Index Tuning
Edit `database/migrations/00_add_vector_tables.sql`:
```sql
CREATE INDEX ... WITH (lists = 100);  -- Adjust based on dataset size
-- Rule of thumb: lists ≈ sqrt(row_count)
```

## Retraining

Retrain periodically to update embeddings with new data:

```bash
# Manual retrain
curl -X POST http://localhost:8000/retrain

# Scheduled (via cron)
0 2 * * * curl -X POST http://localhost:8000/retrain
```

## Troubleshooting

### pgvector not found

**Error**: `ERROR: extension "vector" is not available`

**Solution**: Install pgvector extension:
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-server-dev-all
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install

# Then enable in your database
psql -c "CREATE EXTENSION vector;"
```

### No recommendations returned

**Error**: Recommendations return empty list

**Solution**:
1. Check if embeddings exist: `SELECT COUNT(*) FROM product_embeddings;`
2. If 0, run retrain: `curl -X POST http://localhost:8000/retrain`
3. Verify products have text content: `SELECT COUNT(*) FROM products WHERE description IS NOT NULL;`

### Slow queries

**Symptom**: Queries take > 1 second

**Solution**:
1. Update statistics: `ANALYZE product_embeddings; ANALYZE customer_embeddings;`
2. Check index usage: `EXPLAIN ANALYZE SELECT ...`
3. Increase `lists` parameter in index definition
4. Consider upgrading to HNSW index (pgvector 0.5.0+)

## Testing

Run the test suite:
```bash
pytest tests/test_pgvector_integration.py -v
```

Tests verify:
- pgvector extension is enabled
- Tables and indexes exist
- Embeddings can be stored and retrieved
- Recommendations exclude purchased items
- Query performance is acceptable

## Development

### Project Structure
```
ml-service/
├── app/
│   ├── main.py                              # FastAPI application
│   ├── models/
│   │   └── schemas.py                       # Pydantic models
│   └── services/
│       ├── database.py                      # DB service with pgvector methods
│       ├── content_based_recommender.py     # Content-based (pgvector-backed)
│       ├── recommendation_engine.py         # Collaborative filtering (pgvector-backed)
│       ├── customer_embedding_generator.py  # Customer embeddings from purchases
│       └── hybrid_recommender.py            # Hybrid strategy
├── tests/
│   └── test_pgvector_integration.py         # Integration tests
├── requirements.txt                          # Python dependencies
└── Dockerfile                                # Docker container definition
```

### Adding New Recommendation Strategies

1. Create new recommender class in `app/services/`
2. Implement `get_recommendations(customer_id, top_n)` method
3. Use `self.db.get_product_embedding()` or `recommend_products_pgvector()` for similarity search
4. Register in `app/main.py` endpoints

## Docker Deployment

```bash
# Build image
docker build -t ml-service .

# Run container
docker run -p 8000:8000 \
  -e DB_HOST=host.docker.internal \
  -e DB_NAME=ecommerce \
  -e DB_USER=postgres \
  -e DB_PASSWORD=password \
  ml-service
```

## License

MIT

## Support

For issues or questions:
1. Check the logs: `tail -f logs/*.log`
2. Verify database connectivity
3. Run test suite for diagnostics
4. Review API documentation at `/docs`
