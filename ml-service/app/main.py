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
    SimilarCustomerResponse,
    HealthResponse,
    MetricsResponse
)
from app.services.recommendation_engine import RecommendationEngine
from app.services.database import DatabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db_service = None
recommendation_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db_service, recommendation_engine

    # Startup
    logger.info("Starting ML Recommendation Service...")

    try:
        # Initialize database service
        db_service = DatabaseService()
        logger.info("✓ Database service initialized")

        # Initialize recommendation engine
        recommendation_engine = RecommendationEngine(db_service)

        # Load and train model
        logger.info("Loading data and training model...")
        recommendation_engine.load_data()
        recommendation_engine.compute_similarity()
        logger.info("✓ Model trained and ready")

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
    description="AI-powered product recommendation service using collaborative filtering",
    version="1.0.0",
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
        model_loaded = recommendation_engine.is_ready()

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

# Get recommendations endpoint
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

        similar = recommendation_engine.get_similar_customers(
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

# Retrain model endpoint
@app.post("/retrain", tags=["Model Management"])
async def retrain_model():
    """
    Retrain the recommendation model with latest data.
    This should be called periodically or after significant data changes.
    """
    try:
        logger.info("Retraining model...")

        recommendation_engine.load_data()
        recommendation_engine.compute_similarity()

        logger.info("✓ Model retrained successfully")

        return {
            "status": "success",
            "message": "Model retrained successfully",
            "customers": recommendation_engine.get_customer_count(),
            "products": recommendation_engine.get_product_count()
        }

    except Exception as e:
        logger.error(f"Error retraining model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get model metrics endpoint
@app.get("/metrics", response_model=MetricsResponse, tags=["Model Management"])
async def get_metrics():
    """Get model performance metrics and statistics"""
    try:
        metrics = recommendation_engine.get_metrics()

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

# Root endpoint
@app.get("/", tags=["Info"])
async def root():
    """API information"""
    return {
        "name": "E-Commerce Recommendation API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
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
