# Hybrid Recommendation System Architecture

## Overview

This e-commerce recommendation system implements a **production-grade hybrid approach** combining multiple recommendation strategies to provide personalized product suggestions. The system supports four distinct recommendation algorithms that can be selected via API parameters.

## Recommendation Strategies

### 1. Collaborative Filtering (CF) - `strategy=cf`

**Algorithm**: User-User Collaborative Filtering  
**Approach**: Finds customers with similar purchase patterns and recommends products they bought

**How it works**:
- Creates a customer-product matrix from purchase history
- Computes cosine similarity between customers
- For a target customer, finds the top-N most similar customers
- Recommends products purchased by similar customers (that the target hasn't bought)
- Scores are weighted by customer similarity

**Best for**:
- Customers with substantial purchase history
- Discovering products based on community behavior
- "Customers who bought X also bought Y" scenarios

**Technical Details**:
```python
# User-item matrix normalization
normalized = StandardScaler().fit_transform(user_item_matrix)

# Cosine similarity computation
similarity_matrix = cosine_similarity(normalized)

# Weighted scoring
score = Σ(similarity[i] × purchases[i]) for similar customers i
```

### 2. Content-Based Filtering - `strategy=content`

**Algorithm**: TF-IDF + Cosine Similarity on Product Metadata  
**Approach**: Recommends products similar to what the customer has purchased

**How it works**:
- Extracts product features: name, category, description
- Creates TF-IDF vectors from combined text features
- Computes product-product similarity matrix
- For each product a customer bought, finds similar products
- Aggregates similarity scores across all purchased products

**Best for**:
- New customers with limited purchase history
- Customers with strong category preferences
- "More like this" recommendations

**Technical Details**:
```python
# Feature engineering
product_content = name + ' ' + category + ' ' + description

# TF-IDF vectorization
tfidf_vectorizer = TfidfVectorizer(
    max_features=500,
    stop_words='english',
    ngram_range=(1, 2)
)
tfidf_matrix = tfidf_vectorizer.fit_transform(product_content)

# Product similarity
product_similarity = cosine_similarity(tfidf_matrix)
```

### 3. Hybrid Strategy - `strategy=hybrid` (Default)

**Algorithm**: Weighted Combination of CF + Content-Based  
**Approach**: Combines collaborative and content-based scores with configurable weights

**How it works**:
- Generates recommendations from both CF and content-based models
- Combines scores using weighted average:
  ```
  final_score = 0.6 × cf_score + 0.4 × content_score
  ```
- Returns top-N products by combined score

**Best for**:
- General-purpose recommendations
- Balancing personalization with product similarity
- Production deployments (most robust)

**Advantages**:
- Mitigates cold-start problem (content-based helps new users)
- Reduces filter bubble effect (CF adds diversity)
- More robust to sparse data
- Better coverage across product catalog

**Weight Tuning**:
The default weights (60% CF, 40% content) can be adjusted:
```python
hybrid_recommender.set_weights(cf_weight=0.7, content_weight=0.3)
```

### 4. Popularity-Based - `strategy=popular`

**Algorithm**: Trending Products by Purchase Count  
**Approach**: Returns most frequently purchased products

**How it works**:
- Counts total purchases per product
- Ranks products by purchase frequency
- Returns top-N most popular items

**Best for**:
- Cold-start scenarios (brand new users)
- Homepage "Trending Now" sections
- Fallback when personalization fails

## API Usage

### Get Recommendations

```bash
# Hybrid recommendations (default)
GET /recommendations/123?strategy=hybrid&limit=5

# Collaborative filtering
GET /recommendations/123?strategy=cf&limit=10

# Content-based
GET /recommendations/123?strategy=content&limit=5

# Popular products
GET /recommendations/123?strategy=popular&limit=10
```

**Response Format**:
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

### Additional Endpoints

```bash
# Find similar customers (CF-based)
GET /similar-customers/123?limit=5

# Find similar products (content-based)
GET /similar-products/42?limit=5

# Retrain all models
POST /retrain

# Get system metrics
GET /metrics

# Health check
GET /health
```

## Architecture Components

### 1. Database Service (`database.py`)
- PostgreSQL connection management
- Purchase matrix queries
- Product metadata retrieval
- Popularity statistics

### 2. Collaborative Filtering Engine (`recommendation_engine.py`)
- User-item matrix construction
- Customer similarity computation
- Personalized recommendations
- Similar customer discovery

### 3. Content-Based Recommender (`content_based_recommender.py`)
- Product feature extraction
- TF-IDF vectorization
- Product similarity matrix
- Content-based recommendations

### 4. Hybrid Recommender (`hybrid_recommender.py`)
- Score combination logic
- Weight management
- Fallback handling
- Unified recommendation interface

### 5. FastAPI Application (`main.py`)
- REST API endpoints
- Strategy routing
- Error handling
- Model lifecycle management

## Performance Characteristics

| Strategy | Cold Start | Sparsity | Diversity | Personalization | Scalability |
|----------|-----------|----------|-----------|-----------------|-------------|
| CF       | Poor      | Sensitive| High      | High            | O(n²)       |
| Content  | Good      | Robust   | Low       | Medium          | O(m²)       |
| Hybrid   | Good      | Robust   | Medium    | High            | O(n²+m²)    |
| Popular  | Excellent | Immune   | Low       | None            | O(1)        |

*n = customers, m = products*

## Model Training

### Initial Training (Startup)
```python
# Collaborative filtering
cf_recommender.load_data()
cf_recommender.compute_similarity()

# Content-based
content_recommender.load_data()
content_recommender.compute_similarity()

# Hybrid (uses both)
hybrid_recommender = HybridRecommender(cf_recommender, content_recommender)
```

### Retraining Strategy
- **Trigger**: POST /retrain endpoint
- **Frequency**: Daily or after significant data changes
- **Duration**: Depends on data size (typically seconds to minutes)
- **Downtime**: None (models updated atomically)

## Production Considerations

### Scalability
- **Precompute**: Similarity matrices computed offline
- **Caching**: Consider Redis for hot recommendations
- **Batch Processing**: Retrain during low-traffic periods
- **Horizontal Scaling**: Stateless API allows multiple instances

### Monitoring
- Track strategy usage distribution
- Monitor recommendation diversity
- Measure click-through rates per strategy
- Alert on model staleness

### A/B Testing
The strategy parameter enables easy A/B testing:
```python
# Route 50% to hybrid, 50% to CF
strategy = random.choice(['hybrid', 'cf'])
recommendations = get_recommendations(customer_id, strategy=strategy)
```

## Future Enhancements

1. **Deep Learning**: Add neural collaborative filtering
2. **Context-Aware**: Incorporate time, location, device
3. **Multi-Armed Bandits**: Exploration vs exploitation
4. **Real-Time Updates**: Streaming model updates
5. **Explainability**: Enhanced reasoning for recommendations
6. **Diversity Optimization**: Post-processing for variety

## Resume/Portfolio Highlights

This implementation demonstrates:

✅ **Multiple ML Algorithms**: CF, content-based, hybrid, popularity  
✅ **Production Architecture**: FastAPI, PostgreSQL, Docker  
✅ **Scalable Design**: Precomputed similarities, stateless API  
✅ **Industry Best Practices**: Hybrid approach, cold-start handling  
✅ **Full-Stack Integration**: ML service + Node.js backend + React frontend  
✅ **API Design**: RESTful, strategy pattern, comprehensive documentation  

**Key Talking Points**:
- "Designed and implemented hybrid recommender system combining collaborative filtering (60%) and content-based filtering (40%)"
- "Achieved robust cold-start handling through multi-strategy approach with popularity-based fallback"
- "Built production-ready ML API with FastAPI serving 4 recommendation algorithms via strategy parameter"
- "Implemented TF-IDF-based content similarity and cosine similarity for user-user collaborative filtering"
