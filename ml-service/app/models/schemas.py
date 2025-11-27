"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class RecommendationStrategy(str, Enum):
    COLLABORATIVE = "cf"
    CONTENT_BASED = "content"
    HYBRID = "hybrid"
    POPULAR = "popular"

class RecommendationResponse(BaseModel):
    """Response model for product recommendations"""
    product_id: int = Field(..., description="Product ID")
    score: float = Field(..., description="Recommendation score", ge=0)
    reason: str = Field(..., description="Reason for recommendation")
    name: Optional[str] = Field(None, description="Product name")
    category: Optional[str] = Field(None, description="Product category")
    price: Optional[float] = Field(None, description="Product price")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": 42,
                "score": 0.85,
                "reason": "hybrid",
                "name": "Wireless Headphones",
                "category": "Electronics",
                "price": 79.99
            }
        }

class SimilarCustomerResponse(BaseModel):
    """Response model for similar customers"""
    customer_id: int = Field(..., description="Customer ID")
    similarity_score: float = Field(..., description="Similarity score", ge=0, le=1)

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": 123,
                "similarity_score": 0.92
            }
        }

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    database_connected: bool = Field(..., description="Database connection status")
    model_loaded: bool = Field(..., description="Model loaded status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "database_connected": True,
                "model_loaded": True
            }
        }

class MetricsResponse(BaseModel):
    """Model metrics response"""
    total_customers: int = Field(..., description="Total number of customers")
    total_products: int = Field(..., description="Total number of products")
    total_purchases: int = Field(..., description="Total number of purchases")
    avg_purchases_per_customer: float = Field(..., description="Average purchases per customer")
    model_last_trained: Optional[datetime] = Field(None, description="Last training timestamp")
    sparsity: float = Field(..., description="User-item matrix sparsity", ge=0, le=1)

    class Config:
        json_schema_extra = {
            "example": {
                "total_customers": 500,
                "total_products": 100,
                "total_purchases": 2500,
                "avg_purchases_per_customer": 5.0,
                "model_last_trained": "2024-01-15T10:30:00",
                "sparsity": 0.95
            }
        }
