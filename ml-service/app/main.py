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
from app.services.customer_embedding_generator import CustomerEmbeddingGenerator
from app.services.database import DatabaseService
from app.services.cache import CacheService

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
customer_embedding_generator = None
cache_service: Optional[CacheService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db_service, cf_recommender, content_recommender, hybrid_recommender, customer_embedding_generator

    # Startup
    logger.info("Starting ML Recommendation Service...")

    try:
        # Initialize database service
        db_service = DatabaseService()
        logger.info("✓ Database service initialized")

        # Initialize collaborative filtering recommender
        cf_recommender = RecommendationEngine(db_service)
        logger.info("✓ Collaborative filtering engine initialized")

        # Initialize content-based recommender
        content_recommender = ContentBasedRecommender(db_service)
        logger.info("✓ Content-based engine initialized")

        # Initialize customer embedding generator
        customer_embedding_generator = CustomerEmbeddingGenerator(db_service)
        logger.info("✓ Customer embedding generator ready")

        # Initialize hybrid recommender
        hybrid_recommender = HybridRecommender(
            collaborative_recommender=cf_recommender,
            content_based_recommender=content_recommender,
            cf_weight=0.6,
            content_weight=0.4
        )
        logger.info("✓ Hybrid recommender ready")
        
        # Initialize cache service (Redis)
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        cache_ttl = int(os.getenv('CACHE_TTL', '300'))
        cache_service = CacheService(url=redis_url, ttl=cache_ttl)
        try:
            await cache_service.connect()
        except Exception:
            logger.warning("Redis cache not available; continuing without cache")

        logger.info("⚠️  Run POST /retrain to load data and compute embeddings")

        yield

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down ML Recommendation Service...")
        if db_service:
            db_service.close()
        if cache_service:
            await cache_service.close()

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
        recommendations_ready = (
            cf_recommender.is_ready() and
            content_recommender is not None and
            hybrid_recommender is not None
        )

        status = "healthy" if (db_healthy and recommendations_ready) else "unhealthy"

        return HealthResponse(
            status=status,
            database_connected=db_healthy,
            recommendations_ready=recommendations_ready
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            database_connected=False,
            recommendations_ready=False
        )


@app.get(
    "/recommendations/{customer_id}",
    response_model=List[RecommendationResponse],
    tags=["Recommendations"]
)
async def get_recommendations(
    customer_id: int,
    limit: int = Query(default=5, ge=1, le=20, description="Number of recommendations"),
    strategy: RecommendationStrategy = Query(default=RecommendationStrategy.HYBRID, description="Recommendation strategy")
):
    """
    Get personalized product recommendations for a customer.

    - **customer_id**: Customer ID
    - **limit**: Number of recommendations to return (1-20)
    - **strategy**: Recommendation strategy (hybrid, cf, content, popular)

    Returns list of recommended products with scores and reasoning.
    
    Note: All strategies now use pgvector-backed embeddings for similarity search.
    """
    try:
        logger.info(f"Getting {strategy} recommendations for customer {customer_id}")

        # Check cache first
        cached = None
        try:
            if cache_service:
                cached = await cache_service.get_recommendations(customer_id, strategy.name.lower(), limit)
        except Exception:
            cached = None

        if cached:
            logger.info(f"Returning cached recommendations for customer {customer_id} (strategy={strategy})")
            return [RecommendationResponse(**r) for r in cached]

        # Select recommender based on strategy
        if strategy == RecommendationStrategy.HYBRID:
            recommendations = hybrid_recommender.get_recommendations(
                customer_id=customer_id,
                top_n=limit
            )
        elif strategy == RecommendationStrategy.COLLABORATIVE:
            recommendations = cf_recommender.get_recommendations(
                customer_id=customer_id,
                top_n=limit
            )
        elif strategy == RecommendationStrategy.CONTENT_BASED:
            recommendations = content_recommender.get_recommendations(
                customer_id=customer_id,
                top_n=limit
            )
        elif strategy == RecommendationStrategy.POPULAR:
            popular_products = db_service.get_popular_products(limit=limit)
            recommendations = [
                {
                    'product_id': p['product_id'],
                    'score': p['purchase_count'] / 100.0,
                    'reason': 'popular'
                }
                for p in popular_products
            ]
        else:
            raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy}")

        response = [
            RecommendationResponse(
                product_id=rec['product_id'],
                score=rec['score'],
                reason=rec['reason']
            )
            for rec in recommendations
        ]

        # Store in cache (best-effort)
        try:
            if cache_service:
                # Serialize list of dicts
                await cache_service.set_recommendations(customer_id, strategy.name.lower(), limit, [r.dict() for r in response])
        except Exception as e:
            logger.debug(f"Failed to set recommendation cache: {e}")

        return response

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
    Retrain all recommendation models and persist embeddings to pgvector.
    
    This endpoint:
    1. Loads purchase and product data
    2. Computes collaborative filtering (customer embeddings)
    3. Computes content-based filtering (product embeddings via TF-IDF)
    4. Generates customer preference embeddings
    5. Stores all embeddings to database with version tracking
    
    Returns:
        - model_version_id: ID of the created model version
        - product_embeddings: Number of product embeddings stored
        - customer_embeddings_cf: Number of CF-based customer embeddings
        - customer_embeddings_content: Number of content-based customer embeddings
        - customers: Total customers in model
        - products: Total products in model
    """
    try:
        if not db_service.pgvector_enabled:
            raise HTTPException(
                status_code=503,
                detail="pgvector extension is required but not enabled. Please install and enable pgvector."
            )
        
        logger.info("Starting model retrain with pgvector embedding storage...")

        # Load collaborative filtering data
        cf_recommender.load_data()
        
        # Load content-based data
        content_recommender.load_data()
        
        # Determine embedding dimensions
        cf_dim = cf_recommender.get_embedding_dimension()  # Based on number of products
        content_dim = content_recommender.get_embedding_dimension()  # Based on TF-IDF features
        
        logger.info(f"CF dimension: {cf_dim}, Content dimension: {content_dim}")

        # Create model version record
        model_version_id = db_service.log_new_model_version(
            name="hybrid_recommendation_model",
            dimension=content_dim,  # Use content dimension for product embeddings
            params={
                "content_based": {
                    "tfidf_max_features": content_recommender.tfidf_vectorizer.max_features,
                    "ngram_range": list(content_recommender.tfidf_vectorizer.ngram_range)
                },
                "collaborative_filtering": {
                    "cf_embedding_dim": cf_dim,
                    "normalization": "l2"
                }
            },
            metrics={
                "total_customers": cf_recommender.get_customer_count(),
                "total_products": cf_recommender.get_product_count(),
                "matrix_sparsity": cf_recommender._calculate_sparsity()
            }
        )

        logger.info(f"✓ Created model version {model_version_id}")

        # Compute and store product embeddings (content-based TF-IDF)
        content_recommender.compute_similarity(model_version_id)
        
        # Compute and store customer embeddings (CF-based)
        cf_recommender.compute_similarity(model_version_id)
        
        # Generate and store customer embeddings (content-based: aggregated from purchases)
        customer_count_content = customer_embedding_generator.generate_and_store_embeddings(
            model_version_id,
            weight_by_quantity=True
        )
        
        # Get final counts
        embedding_counts = db_service.count_embeddings()

        logger.info("✓ All models retrained and embeddings persisted successfully")
        # Invalidate recommendation cache after retrain
        try:
            if cache_service:
                await cache_service.invalidate_all_recommendations()
                logger.info("✓ Invalidated all recommendation cache after retrain")
        except Exception:
            logger.warning("Failed to invalidate cache after retrain")

        return {
            "status": "success",
            "message": "All models retrained and embeddings stored in database",
            "model_version_id": model_version_id,
            "customers": cf_recommender.get_customer_count(),
            "products": cf_recommender.get_product_count(),
            "product_embeddings": embedding_counts['products'],
            "customer_embeddings": embedding_counts['customers'],
            "embedding_dimension": content_dim
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
            last_trained_at=metrics['model_last_trained'],
            sparsity=metrics['sparsity']
        )

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cache/invalidate/{customer_id}", tags=["Cache"])
async def invalidate_customer_cache(customer_id: int):
    """Invalidate cache entries for a specific customer"""
    try:
        if cache_service:
            await cache_service.invalidate_recommendations_for_customer(customer_id)
            return {"status": "ok", "message": f"Invalidated cache for customer {customer_id}"}
        else:
            raise HTTPException(status_code=503, detail="Cache service not available")
    except Exception as e:
        logger.error(f"Error invalidating cache for {customer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cache/invalidate_all", tags=["Cache"])
async def invalidate_all_cache():
    """Invalidate all recommendation cache entries"""
    try:
        if cache_service:
            await cache_service.invalidate_all_recommendations()
            return {"status": "ok", "message": "Invalidated all recommendation cache"}
        else:
            raise HTTPException(status_code=503, detail="Cache service not available")
    except Exception as e:
        logger.error(f"Error invalidating all cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", tags=["Info"])
async def root():
    """API information"""
    embedding_counts = db_service.count_embeddings() if db_service else {'products': 0, 'customers': 0, 'model_versions': 0}
    
    return {
        "name": "E-Commerce Recommendation API",
        "version": "2.0.0",
        "status": "running",
        "pgvector_enabled": db_service.pgvector_enabled if db_service else False,
        "embeddings": embedding_counts,
        "strategies": {
            "cf": "Collaborative Filtering (pgvector-backed customer similarity)",
            "content": "Content-Based Filtering (pgvector-backed product similarity)",
            "hybrid": "Hybrid (60% CF + 40% Content, both pgvector-backed)",
            "popular": "Popularity-Based (trending products)"
        },
        "note": "All recommendation strategies now use pgvector for embeddings storage and similarity search",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "recommendations": "/recommendations/{customer_id}?strategy=hybrid&limit=5",
            "similar_customers": "/similar-customers/{customer_id}",
            "similar_products": "/similar-products/{product_id}",
            "metrics": "/metrics",
            "retrain": "/retrain (POST - required before first use)"
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
