# API Documentation

## ML Service API (Port 8000)

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Get Recommendations
Get personalized product recommendations for a customer.

**Endpoint:** `GET /recommendations/{customer_id}`

**Parameters:**
- `customer_id` (path, required): Customer ID
- `limit` (query, optional): Number of recommendations (default: 5, max: 20)

**Response:**
```json
[
  {
    "product_id": 42,
    "score": 0.85,
    "reason": "customers_like_you"
  }
]
```

#### 2. Get Similar Customers
Find customers with similar purchase patterns.

**Endpoint:** `GET /similar-customers/{customer_id}`

**Parameters:**
- `customer_id` (path, required): Customer ID
- `limit` (query, optional): Number of similar customers (default: 5)

**Response:**
```json
[
  {
    "customer_id": 123,
    "similarity_score": 0.92
  }
]
```

#### 3. Retrain Model
Trigger model retraining with latest data.

**Endpoint:** `POST /retrain`

**Response:**
```json
{
  "status": "success",
  "message": "Model retrained successfully",
  "customers": 500,
  "products": 100
}
```

#### 4. Health Check
Check service health.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "database_connected": true,
  "model_loaded": true
}
```

#### 5. Get Metrics
Get model performance metrics.

**Endpoint:** `GET /metrics`

**Response:**
```json
{
  "total_customers": 500,
  "total_products": 100,
  "total_purchases": 2500,
  "avg_purchases_per_customer": 5.0,
  "model_last_trained": "2024-01-15T10:30:00",
  "sparsity": 0.95
}
```

---

## Backend API (Port 5000)

### Base URL
```
http://localhost:5000/api
```

### Products Endpoints

#### Get All Products
**Endpoint:** `GET /products`

**Parameters:**
- `category` (query, optional): Filter by category
- `limit` (query, optional): Number of products (default: 50)
- `offset` (query, optional): Pagination offset (default: 0)

**Response:**
```json
{
  "products": [...],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

#### Get Product by ID
**Endpoint:** `GET /products/{id}`

#### Get Product Recommendations
**Endpoint:** `GET /products/recommendations/{customerId}`

Returns enriched recommendations with full product details.

#### Get Categories
**Endpoint:** `GET /products/meta/categories`

### Customer Endpoints

#### Get Customer
**Endpoint:** `GET /customers/{id}`

#### Get Purchase History
**Endpoint:** `GET /customers/{id}/history`

**Parameters:**
- `limit` (query, optional): Number of purchases (default: 20)
- `offset` (query, optional): Pagination offset

#### Get Customer Analytics
**Endpoint:** `GET /customers/{id}/analytics`

Returns customer analytics including total purchases, spending, favorite category, etc.

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": "Error message"
}
```

**Status Codes:**
- `200`: Success
- `404`: Not Found
- `500`: Internal Server Error
