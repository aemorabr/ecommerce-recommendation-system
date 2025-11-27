# ML Model Documentation

## Overview

This recommendation system uses **Collaborative Filtering** based on customer-customer similarity to generate personalized product recommendations.

## Algorithm: User-Based Collaborative Filtering

### How It Works

1. **User-Item Matrix Construction**
   - Rows: Customers
   - Columns: Products
   - Values: Purchase quantities
   - Sparse matrix (most customers haven't bought most products)

2. **Similarity Computation**
   - Normalize purchase quantities using StandardScaler
   - Compute cosine similarity between customer vectors
   - Result: Similarity matrix where `sim[i][j]` = similarity between customer i and j

3. **Recommendation Generation**
   - For target customer, find K most similar customers
   - Identify products purchased by similar customers
   - Filter out products already purchased by target customer
   - Score remaining products by weighted sum of similar customers' purchases
   - Return top N products

### Mathematical Formulation

**Cosine Similarity:**
```
sim(u, v) = (u · v) / (||u|| × ||v||)
```

**Recommendation Score:**
```
score(user, product) = Σ(similarity(user, similar_user) × purchases(similar_user, product))
```

## Model Performance

### Metrics

- **Sparsity**: ~95% (typical for e-commerce)
- **Coverage**: 100% (all products can be recommended)
- **Latency**: <100ms for recommendations
- **Cold Start**: Falls back to popular items

### Evaluation

The model is evaluated on:
1. **Precision@K**: Accuracy of top K recommendations
2. **Recall@K**: Coverage of relevant items in top K
3. **NDCG**: Ranking quality

## Advantages

✅ **Interpretable**: "Customers like you bought this"
✅ **No feature engineering**: Works with purchase data only
✅ **Handles new products**: New products appear in recommendations immediately
✅ **Personalized**: Different recommendations for each customer

## Limitations

⚠️ **Cold Start**: New customers with no purchases get popular items
⚠️ **Scalability**: Similarity matrix is O(n²) in memory
⚠️ **Sparsity**: Performance degrades with very sparse data
⚠️ **Popularity Bias**: Tends to recommend popular items

## Future Improvements

### 1. Matrix Factorization
Use SVD or ALS to reduce dimensionality and improve scalability.

```python
from sklearn.decomposition import TruncatedSVD

svd = TruncatedSVD(n_components=50)
user_factors = svd.fit_transform(user_item_matrix)
item_factors = svd.components_
```

### 2. Deep Learning
Implement Neural Collaborative Filtering (NCF) for better accuracy.

```python
import torch
import torch.nn as nn

class NCF(nn.Module):
    def __init__(self, num_users, num_items, embedding_dim=64):
        super().__init__()
        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.item_embedding = nn.Embedding(num_items, embedding_dim)
        self.fc = nn.Sequential(
            nn.Linear(embedding_dim * 2, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
```

### 3. Hybrid Approach
Combine collaborative filtering with content-based filtering using product features.

### 4. Context-Aware
Incorporate temporal patterns, seasonality, and user context.

### 5. A/B Testing
Implement online evaluation to measure real-world impact.

## Retraining Strategy

### When to Retrain
- **Scheduled**: Weekly (Sunday 2 AM)
- **Triggered**: After significant data changes (>10% new purchases)
- **Manual**: Via API endpoint

### Retraining Process
1. Load latest purchase data from database
2. Rebuild user-item matrix
3. Recompute similarity matrix
4. Update model timestamp
5. Validate model health

### Monitoring
- Track model metrics over time
- Alert on significant performance drops
- Monitor recommendation diversity
- Track cold-start rate

## Code Structure

```
ml-service/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── models/
│   │   └── schemas.py             # Pydantic models
│   └── services/
│       ├── database.py            # Database operations
│       └── recommendation_engine.py  # Core ML logic
├── tests/                         # Unit tests
├── requirements.txt               # Dependencies
└── Dockerfile                     # Container definition
```

## API Integration

The ML service exposes a REST API that can be consumed by any backend:

```python
# Example: Get recommendations
import requests

response = requests.get(
    'http://ml-service:8000/recommendations/123',
    params={'limit': 5}
)

recommendations = response.json()
# [{'product_id': 42, 'score': 0.85, 'reason': 'customers_like_you'}, ...]
```

## Performance Optimization

### Current Optimizations
- ✅ Vectorized operations with NumPy
- ✅ Efficient sparse matrix handling
- ✅ Database connection pooling
- ✅ Precomputed similarity matrix

### Future Optimizations
- [ ] Approximate nearest neighbors (Annoy, FAISS)
- [ ] Caching frequent recommendations
- [ ] Incremental model updates
- [ ] GPU acceleration for large datasets

## References

- [Collaborative Filtering - Wikipedia](https://en.wikipedia.org/wiki/Collaborative_filtering)
- [Matrix Factorization Techniques for Recommender Systems](https://datajobs.com/data-science-repo/Recommender-Systems-[Netflix].pdf)
- [Neural Collaborative Filtering](https://arxiv.org/abs/1708.05031)
