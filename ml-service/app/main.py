"""
FastAPI ML Recommendation Service
Main application entry point
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import List, Optional
import os

from app.models.schemas import (
    RecommendationResponse,
    RecommendationStrategy,
    SimilarCustomerResponse,
    HealthResponse,
    MetricsResponse
)
from app.services.recommendation_engine import RecommendationEngine
from app.services.content_based_recommender import ContentBasedRecommender
from app.services.hybrid_recommender import HybridRecommender
from app.services.database import DatabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db_service = None
cf_recommender = None
content_recommender = None
hybrid_recommender = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db_service, cf_recommender, content_recommender, hybrid_recommender

    # Startup
    logger.info("Starting ML Recommendation Service...")

    try:
        # Initialize database service
        db_service = DatabaseService()
        logger.info("✓ Database service initialized")

        # Initialize collaborative filtering recommender
        cf_recommender = RecommendationEngine(db_service)
        logger.info("Loading data and training collaborative filtering model...")
        cf_recommender.load_data()
        cf_recommender.compute_similarity()
        logger.info("✓ Collaborative filtering model ready")

        # Initialize content-based recommender
        content_recommender = ContentBasedRecommender(db_service)
        logger.info("Loading data and training content-based model...")
        content_recommender.load_data()
        content_recommender.compute_similarity()
        logger.info("✓ Content-based model ready")

        # Initialize hybrid recommender
        hybrid_recommender = HybridRecommender(
            collaborative_recommender=cf_recommender,
            content_based_recommender=content_recommender,
            cf_weight=0.6,
            content_weight=0.4
        )
        logger.info("✓ Hybrid recommender ready")

        yield

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down ML Recommendation Service...")
        if db_service:
            db_service.close()

# Create FastAPI app
app = FastAPI(
    title="E-Commerce Recommendation API",
    description="Hybrid AI-powered product recommendation service using collaborative filtering, content-based filtering, and popularity-based strategies",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check service health status"""
    try:
        # Check database connection
        db_healthy = db_service.check_connection()

        # Check model status
        model_loaded = (
            cf_recommender.is_ready() and
            content_recommender is not None and
            hybrid_recommender is not None
        )

        status = "healthy" if (db_healthy and model_loaded) else "unhealthy"

        return HealthResponse(
            status=status,
            database_connected=db_healthy,
            model_loaded=model_loaded
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            database_connected=False,
            model_loaded=False
        )


@app.get(
    "/recommendations/{customer_id}",
    response_model=List[RecommendationResponse],
    tags=["Recommendations"]
)
async def get_recommendations(
    customer_id: int,
    limit: int = Query(default=5, ge=1, le=20, description="Number of recommendations")
):
    """
    Get personalized product recommendations for a customer.

    - **customer_id**: Customer ID
    - **limit**: Number of recommendations to return (1-20)

    Returns list of recommended products with scores and reasoning.
    """
    try:
        logger.info(f"Getting recommendations for customer {customer_id}")

        recommendations = recommendation_engine.get_recommendations(
            customer_id=customer_id,
            top_n=limit
        )

        return [
            RecommendationResponse(
                product_id=rec['product_id'],
                score=rec['score'],
                reason=rec['reason']
            )
            for rec in recommendations
        ]

    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get similar customers endpoint
@app.get(
    "/similar-customers/{customer_id}",
    response_model=List[SimilarCustomerResponse],
    tags=["Recommendations"]
)
async def get_similar_customers(
    customer_id: int,
    limit: int = Query(default=5, ge=1, le=20)
):
    """
    Find customers with similar purchase patterns.

    - **customer_id**: Customer ID
    - **limit**: Number of similar customers to return
    """
    try:
        logger.info(f"Finding similar customers for {customer_id}")

        similar = cf_recommender.get_similar_customers(
            customer_id=customer_id,
            top_n=limit
        )

        return [
            SimilarCustomerResponse(
                customer_id=s['customer_id'],
                similarity_score=s['similarity_score']
            )
            for s in similar
        ]

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error finding similar customers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get similar products endpoint
@app.get(
    "/similar-products/{product_id}",
    response_model=List[RecommendationResponse],
    tags=["Recommendations"]
)
async def get_similar_products(
    product_id: int,
    limit: int = Query(default=5, ge=1, le=20)
):
    """
    Find products similar to a given product.

    - **product_id**: Product ID
    - **limit**: Number of similar products to return (1-20)
    """
    try:
        logger.info(f"Finding similar products for {product_id}")

        similar = content_recommender.get_similar_products(
            product_id=product_id,
            top_n=limit
        )

        return [
            RecommendationResponse(
                product_id=rec['product_id'],
                score=rec['score'],
                reason=rec['reason'],
                name=rec.get('name'),
                category=rec.get('category'),
                price=rec.get('price')
            )
            for rec in similar
        ]

    except Exception as e:
        logger.error(f"Error finding similar products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrain", tags=["Model Management"])
async def retrain_model():
    """
    Retrain all recommendation models with latest data.
    This should be called periodically or after significant data changes.
    """
    try:
        logger.info("Retraining all models...")

        cf_recommender.load_data()
        cf_recommender.compute_similarity()

        content_recommender.load_data()
        content_recommender.compute_similarity()

        logger.info("✓ All models retrained successfully")

        return {
            "status": "success",
            "message": "All models retrained successfully",
            "customers": cf_recommender.get_customer_count(),
            "products": cf_recommender.get_product_count()
        }

    except Exception as e:
        logger.error(f"Error retraining model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics", response_model=MetricsResponse, tags=["Model Management"])
async def get_metrics():
    """Get model performance metrics and statistics"""
    try:
        metrics = cf_recommender.get_metrics()

        return MetricsResponse(
            total_customers=metrics['total_customers'],
            total_products=metrics['total_products'],
            total_purchases=metrics['total_purchases'],
            avg_purchases_per_customer=metrics['avg_purchases_per_customer'],
            model_last_trained=metrics['model_last_trained'],
            sparsity=metrics['sparsity']
        )

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", tags=["Info"])
async def root():
    """API information"""
    return {
        "name": "E-Commerce Recommendation API",
        "version": "2.0.0",
        "status": "running",
        "strategies": {
            "cf": "Collaborative Filtering (user-user similarity)",
            "content": "Content-Based Filtering (product similarity)",
            "hybrid": "Hybrid (60% CF + 40% Content)",
            "popular": "Popularity-Based (trending products)"
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "recommendations": "/recommendations/{customer_id}?strategy=hybrid&limit=5",
            "similar_customers": "/similar-customers/{customer_id}",
            "similar_products": "/similar-products/{product_id}",
            "metrics": "/metrics",
            "retrain": "/retrain"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
