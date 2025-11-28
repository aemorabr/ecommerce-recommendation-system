"""
Integration tests for pgvector-based recommendation system
Tests migrations, embeddings storage, and retrieval
"""

import pytest
import psycopg2
import numpy as np
from typing import Dict, Any
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.database import DatabaseService
from app.services.content_based_recommender import ContentBasedRecommender
from app.services.customer_embedding_generator import CustomerEmbeddingGenerator
from app.services.recommendation_engine import RecommendationEngine


class TestPgvectorMigration:
    """Test database migrations and pgvector setup"""

    @pytest.fixture
    def db_service(self):
        """Create database service instance"""
        return DatabaseService()

    def test_pgvector_extension_enabled(self, db_service):
        """Test that pgvector extension is installed"""
        query = "SELECT * FROM pg_extension WHERE extname = 'vector'"
        
        cur = db_service.conn.cursor()
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        
        assert result is not None, "pgvector extension not installed"
        print("✓ pgvector extension is enabled")

    def test_model_versions_table_exists(self, db_service):
        """Test that model_versions table exists"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'model_versions'
            )
        """
        
        cur = db_service.conn.cursor()
        cur.execute(query)
        exists = cur.fetchone()[0]
        cur.close()
        
        assert exists, "model_versions table does not exist"
        print("✓ model_versions table exists")

    def test_product_embeddings_table_exists(self, db_service):
        """Test that product_embeddings table exists with vector column"""
        query = """
            SELECT column_name, data_type 
            FROM information_schema.columns
            WHERE table_name = 'product_embeddings'
        """
        
        cur = db_service.conn.cursor()
        cur.execute(query)
        columns = cur.fetchall()
        cur.close()
        
        column_names = [col[0] for col in columns]
        
        assert 'product_id' in column_names
        assert 'embedding' in column_names
        assert 'model_version_id' in column_names
        assert 'created_at' in column_names
        
        print("✓ product_embeddings table exists with correct schema")

    def test_customer_embeddings_table_exists(self, db_service):
        """Test that customer_embeddings table exists"""
        query = """
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_name = 'customer_embeddings'
        """
        
        cur = db_service.conn.cursor()
        cur.execute(query)
        columns = cur.fetchall()
        cur.close()
        
        column_names = [col[0] for col in columns]
        
        assert 'customer_id' in column_names
        assert 'embedding' in column_names
        assert 'model_version_id' in column_names
        assert 'updated_at' in column_names
        
        print("✓ customer_embeddings table exists with correct schema")

    def test_indexes_created(self, db_service):
        """Test that ANN indexes are created"""
        query = """
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename IN ('product_embeddings', 'customer_embeddings')
        """
        
        cur = db_service.conn.cursor()
        cur.execute(query)
        indexes = cur.fetchall()
        cur.close()
        
        index_names = [idx[0] for idx in indexes]
        
        # Should have at least the ANN indexes
        assert len(index_names) > 0, "No indexes found on embedding tables"
        
        print(f"✓ Found {len(index_names)} indexes on embedding tables")


class TestEmbeddingStorage:
    """Test embedding storage and retrieval"""

    @pytest.fixture
    def db_service(self):
        return DatabaseService()

    def test_create_model_version(self, db_service):
        """Test creating a model version record"""
        if not db_service.pgvector_enabled:
            pytest.skip("pgvector not enabled")
        
        model_version_id = db_service.log_new_model_version(
            name="test_model",
            dimension=128,
            params={"test": "param"},
            metrics={"accuracy": 0.85}
        )
        
        assert model_version_id is not None
        assert isinstance(model_version_id, int)
        
        print(f"✓ Created model version {model_version_id}")

    def test_store_and_retrieve_product_embedding(self, db_service):
        """Test storing and retrieving a product embedding"""
        if not db_service.pgvector_enabled:
            pytest.skip("pgvector not enabled")
        
        # Create model version
        model_version_id = db_service.log_new_model_version(
            name="test_product_embedding",
            dimension=128
        )
        
        # Create a test embedding
        test_embedding = np.random.rand(128).tolist()
        
        # Normalize to unit L2 norm
        from sklearn.preprocessing import normalize
        test_embedding_normalized = normalize(
            np.array(test_embedding).reshape(1, -1),
            norm='l2'
        )[0].tolist()
        
        # Get a real product ID from database
        cur = db_service.conn.cursor()
        cur.execute("SELECT product_id FROM products LIMIT 1")
        result = cur.fetchone()
        cur.close()
        
        if not result:
            pytest.skip("No products in database")
        
        product_id = result[0]
        
        # Store embedding
        db_service.upsert_product_embedding(
            product_id,
            test_embedding_normalized,
            model_version_id
        )
        
        # Retrieve embedding
        retrieved = db_service.get_product_embedding(product_id)
        
        assert retrieved is not None
        assert len(retrieved) == 128
        assert np.allclose(retrieved, test_embedding_normalized, atol=1e-6)
        
        print(f"✓ Successfully stored and retrieved product embedding for product {product_id}")

    def test_store_and_retrieve_customer_embedding(self, db_service):
        """Test storing and retrieving a customer embedding"""
        if not db_service.pgvector_enabled:
            pytest.skip("pgvector not enabled")
        
        # Create model version
        model_version_id = db_service.log_new_model_version(
            name="test_customer_embedding",
            dimension=128
        )
        
        # Create a test embedding
        test_embedding = np.random.rand(128).tolist()
        
        # Normalize
        from sklearn.preprocessing import normalize
        test_embedding_normalized = normalize(
            np.array(test_embedding).reshape(1, -1),
            norm='l2'
        )[0].tolist()
        
        # Get a real customer ID
        cur = db_service.conn.cursor()
        cur.execute("SELECT customer_id FROM customers LIMIT 1")
        result = cur.fetchone()
        cur.close()
        
        if not result:
            pytest.skip("No customers in database")
        
        customer_id = result[0]
        
        # Store embedding
        db_service.upsert_customer_embedding(
            customer_id,
            test_embedding_normalized,
            model_version_id
        )
        
        # Retrieve embedding
        retrieved = db_service.get_customer_embedding(customer_id)
        
        assert retrieved is not None
        assert len(retrieved) == 128
        assert np.allclose(retrieved, test_embedding_normalized, atol=1e-6)
        
        print(f"✓ Successfully stored and retrieved customer embedding for customer {customer_id}")


class TestRetrainWorkflow:
    """Test complete retrain workflow"""

    @pytest.fixture
    def db_service(self):
        return DatabaseService()

    @pytest.fixture
    def content_recommender(self, db_service):
        return ContentBasedRecommender(db_service)

    @pytest.fixture
    def customer_embedding_gen(self, db_service):
        return CustomerEmbeddingGenerator(db_service)

    def test_retrain_creates_model_version(self, db_service, content_recommender):
        """Test that retrain creates a model version"""
        if not db_service.pgvector_enabled:
            pytest.skip("pgvector not enabled")
        
        # Load and compute
        content_recommender.load_data()
        content_recommender.compute_similarity()
        
        # Create model version
        dimension = content_recommender.get_embedding_dimension()
        assert dimension > 0
        
        model_version_id = db_service.log_new_model_version(
            name="retrain_test",
            dimension=dimension
        )
        
        assert model_version_id is not None
        print(f"✓ Created model version {model_version_id} with dimension {dimension}")

    def test_retrain_populates_product_embeddings(
        self, 
        db_service, 
        content_recommender
    ):
        """Test that retrain populates product embeddings"""
        if not db_service.pgvector_enabled:
            pytest.skip("pgvector not enabled")
        
        # Load and compute
        content_recommender.load_data()
        content_recommender.compute_similarity()
        
        # Get dimension and create model version
        dimension = content_recommender.get_embedding_dimension()
        model_version_id = db_service.log_new_model_version(
            name="product_embeddings_test",
            dimension=dimension
        )
        
        # Store embeddings
        count = content_recommender.store_product_embeddings_in_db(model_version_id)
        
        assert count > 0
        print(f"✓ Stored {count} product embeddings")
        
        # Verify in database
        cur = db_service.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM product_embeddings WHERE model_version_id = %s", 
                   (model_version_id,))
        db_count = cur.fetchone()[0]
        cur.close()
        
        assert db_count == count
        assert db_count >= int(0.9 * content_recommender.get_product_count())
        print(f"✓ Verified {db_count} product embeddings in database")

    def test_retrain_populates_customer_embeddings(
        self, 
        db_service, 
        customer_embedding_gen
    ):
        """Test that retrain populates customer embeddings"""
        if not db_service.pgvector_enabled:
            pytest.skip("pgvector not enabled")
        
        # First ensure product embeddings exist
        content_recommender = ContentBasedRecommender(db_service)
        content_recommender.load_data()
        content_recommender.compute_similarity()
        
        dimension = content_recommender.get_embedding_dimension()
        model_version_id = db_service.log_new_model_version(
            name="customer_embeddings_test",
            dimension=dimension
        )
        
        # Store product embeddings first
        content_recommender.store_product_embeddings_in_db(model_version_id)
        
        # Generate customer embeddings
        count = customer_embedding_gen.generate_and_store_embeddings(model_version_id)
        
        assert count > 0
        print(f"✓ Generated {count} customer embeddings")
        
        # Verify in database
        cur = db_service.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM customer_embeddings WHERE model_version_id = %s",
                   (model_version_id,))
        db_count = cur.fetchone()[0]
        cur.close()
        
        assert db_count == count
        print(f"✓ Verified {db_count} customer embeddings in database")


class TestPgvectorRecommendations:
    """Test pgvector-based recommendations"""

    @pytest.fixture
    def db_service(self):
        return DatabaseService()

    @pytest.fixture
    def recommender(self, db_service):
        rec = RecommendationEngine(db_service)
        rec.load_data()
        rec.compute_similarity()
        return rec

    def test_get_recommendations_pgvector_excludes_purchased(
        self, 
        db_service, 
        recommender
    ):
        """Test that pgvector recommendations exclude purchased items"""
        if not db_service.pgvector_enabled:
            pytest.skip("pgvector not enabled")
        
        # Get a customer with purchases
        customers = db_service.get_all_customers_with_purchases()
        
        if not customers:
            pytest.skip("No customers with purchases")
        
        customer_id = customers[0]
        
        # Get purchased products
        purchased = db_service.get_customer_purchased_product_ids(customer_id)
        
        # Get recommendations
        try:
            recommendations = recommender.get_recommendations_pgvector(
                customer_id,
                top_n=10
            )
            
            # Check that no recommended product is already purchased
            recommended_ids = [rec['product_id'] for rec in recommendations]
            
            for product_id in recommended_ids:
                assert product_id not in purchased, \
                    f"Product {product_id} was recommended but already purchased"
            
            print(f"✓ pgvector recommendations for customer {customer_id} exclude {len(purchased)} purchased items")
            
        except Exception as e:
            # If embeddings don't exist yet, that's expected
            if "No embedding found" in str(e) or "No similar customers" in str(e):
                pytest.skip("Customer embeddings not yet populated")
            raise

    def test_similar_customers_pgvector(self, db_service):
        """Test finding similar customers via pgvector"""
        if not db_service.pgvector_enabled:
            pytest.skip("pgvector not enabled")
        
        # Get a customer with an embedding
        cur = db_service.conn.cursor()
        cur.execute("SELECT customer_id FROM customer_embeddings LIMIT 1")
        result = cur.fetchone()
        cur.close()
        
        if not result:
            pytest.skip("No customer embeddings found")
        
        customer_id = result[0]
        
        # Find similar customers
        similar = db_service.get_similar_customers_pgvector(customer_id, k=5)
        
        assert len(similar) > 0
        assert all('customer_id' in s for s in similar)
        assert all('distance' in s for s in similar)
        
        # Ensure distances are sorted
        distances = [s['distance'] for s in similar]
        assert distances == sorted(distances)
        
        print(f"✓ Found {len(similar)} similar customers for customer {customer_id}")


class TestPerformance:
    """Test query performance with indexes"""

    @pytest.fixture
    def db_service(self):
        return DatabaseService()

    def test_product_similarity_query_performance(self, db_service):
        """Test that product similarity queries complete quickly"""
        if not db_service.pgvector_enabled:
            pytest.skip("pgvector not enabled")
        
        # Get a product embedding
        cur = db_service.conn.cursor()
        cur.execute("SELECT embedding FROM product_embeddings LIMIT 1")
        result = cur.fetchone()
        cur.close()
        
        if not result:
            pytest.skip("No product embeddings found")
        
        query_embedding = np.array(result[0])
        
        # Time the query
        import time
        start = time.time()
        
        results = db_service.recommend_products_pgvector(
            query_embedding,
            exclude_product_ids=[],
            top_n=10
        )
        
        elapsed = time.time() - start
        
        assert len(results) > 0
        assert elapsed < 1.0, f"Query took {elapsed:.3f}s (expected < 1.0s)"
        
        print(f"✓ Product similarity query completed in {elapsed:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
