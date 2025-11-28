"""
Database service for PostgreSQL connections and queries
Includes pgvector support for embedding storage and similarity search
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import List, Dict, Any, Optional, Tuple
import logging
import numpy as np

logger = logging.getLogger(__name__)

class DatabaseService:
    """Handle database connections and queries"""

    def __init__(self):
        self.config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'ecommerce'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres'),
            'port': os.getenv('DB_PORT', '5432')
        }
        self.conn = None
        self.pgvector_enabled = False
        self._connect()
        self._try_enable_pgvector()

    def _connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.config)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def _try_enable_pgvector(self):
        """Try to enable pgvector support"""
        try:
            from pgvector.psycopg2 import register_vector
            register_vector(self.conn)
            self.pgvector_enabled = True
            logger.info("✓ pgvector extension registered")
        except ImportError:
            logger.warning("pgvector package not installed - vector operations disabled")
            self.pgvector_enabled = False
        except Exception as e:
            logger.warning(f"Could not register pgvector: {e} - falling back to in-memory mode")
            self.pgvector_enabled = False

    def get_psycopg2_conn(self):
        """Get a psycopg2 connection (creates new or returns existing)"""
        if self.conn is None or self.conn.closed:
            self._connect()
            if self.pgvector_enabled:
                self._try_enable_pgvector()
        return self.conn

    def _ensure_vector_registered(self, conn):
        """Ensure pgvector is registered on the given connection"""
        if self.pgvector_enabled:
            try:
                from pgvector.psycopg2 import register_vector
                register_vector(conn)
            except Exception as e:
                logger.warning(f"Could not register vector on connection: {e}")

    def check_connection(self) -> bool:
        """Check if database connection is alive"""
        try:
            if self.conn is None or self.conn.closed:
                self._connect()

            cur = self.conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False

    def get_purchase_matrix(self) -> List[Dict[str, Any]]:
        """
        Get purchase data for building user-item matrix.
        Returns list of dicts with customer_id, product_id, quantity.
        """
        query = """
            SELECT 
                customer_id,
                product_id,
                SUM(quantity) as quantity
            FROM purchases
            GROUP BY customer_id, product_id
            ORDER BY customer_id, product_id
        """

        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query)
            results = cur.fetchall()
            cur.close()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error fetching purchase matrix: {e}")
            raise

    def get_popular_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular products by purchase count"""
        query = """
            SELECT 
                product_id,
                COUNT(*) as purchase_count
            FROM purchases
            GROUP BY product_id
            ORDER BY purchase_count DESC
            LIMIT %s
        """

        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, (limit,))
            results = cur.fetchall()
            cur.close()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error fetching popular products: {e}")
            raise

    def get_customer_purchases(self, customer_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT DISTINCT p.product_id, pr.name, pr.category, pr.price, pr.description
            FROM purchases p
            JOIN products pr ON p.product_id = pr.product_id
            WHERE p.customer_id = %s
        """

        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, (customer_id,))
            results = cur.fetchall()
            cur.close()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error fetching customer purchases: {e}")
            raise

    def get_all_products(self) -> List[Dict[str, Any]]:
        query = """
            SELECT
                product_id,
                name,
                category,
                price,
                description,
                stock_quantity
            FROM products
            ORDER BY product_id
        """

        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query)
            results = cur.fetchall()
            cur.close()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error fetching all products: {e}")
            raise

    def get_total_customers(self) -> int:
        """Get total number of customers"""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM customers")
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception as e:
            logger.error(f"Error counting customers: {e}")
            raise

    def get_total_products(self) -> int:
        """Get total number of products"""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM products")
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception as e:
            logger.error(f"Error counting products: {e}")
            raise

    def get_total_purchases(self) -> int:
        """Get total number of purchases"""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM purchases")
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception as e:
            logger.error(f"Error counting purchases: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("Database connection closed")

    # ==================== PGVECTOR METHODS ====================

    def log_new_model_version(
        self, 
        name: str, 
        dimension: int, 
        params: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        artifact_url: Optional[str] = None
    ) -> int:
        """
        Create a new model version record and return its ID
        
        Args:
            name: Model name/description
            dimension: Embedding dimension
            params: Model hyperparameters (optional)
            metrics: Model performance metrics (optional)
            artifact_url: URL to model artifacts (optional)
        
        Returns:
            model_version_id
        """
        query = """
            INSERT INTO model_versions (name, dimension, params, metrics, artifact_url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        
        try:
            import json
            cur = self.conn.cursor()
            cur.execute(
                query, 
                (name, dimension, json.dumps(params) if params else None, 
                 json.dumps(metrics) if metrics else None, artifact_url)
            )
            model_version_id = cur.fetchone()[0]
            self.conn.commit()
            cur.close()
            logger.info(f"Created model version {model_version_id}: {name} (dim={dimension})")
            return model_version_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error creating model version: {e}")
            raise

    def upsert_product_embedding(
        self, 
        product_id: int, 
        embedding: List[float], 
        model_version_id: int
    ) -> None:
        """
        Insert or update a product embedding
        
        Args:
            product_id: Product ID
            embedding: Normalized embedding vector
            model_version_id: Reference to model version
        """
        if not self.pgvector_enabled:
            logger.warning("pgvector not enabled - skipping embedding insert")
            return
        
        query = """
            INSERT INTO product_embeddings (product_id, embedding, model_version_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (product_id) 
            DO UPDATE SET 
                embedding = EXCLUDED.embedding,
                model_version_id = EXCLUDED.model_version_id,
                created_at = NOW()
        """
        
        try:
            cur = self.conn.cursor()
            cur.execute(query, (product_id, np.array(embedding), model_version_id))
            self.conn.commit()
            cur.close()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error upserting product embedding for {product_id}: {e}")
            raise

    def upsert_customer_embedding(
        self, 
        customer_id: int, 
        embedding: List[float], 
        model_version_id: int
    ) -> None:
        """
        Insert or update a customer embedding
        
        Args:
            customer_id: Customer ID
            embedding: Normalized embedding vector
            model_version_id: Reference to model version
        """
        if not self.pgvector_enabled:
            logger.warning("pgvector not enabled - skipping embedding insert")
            return
        
        query = """
            INSERT INTO customer_embeddings (customer_id, embedding, model_version_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (customer_id) 
            DO UPDATE SET 
                embedding = EXCLUDED.embedding,
                model_version_id = EXCLUDED.model_version_id,
                updated_at = NOW()
        """
        
        try:
            cur = self.conn.cursor()
            cur.execute(query, (customer_id, np.array(embedding), model_version_id))
            self.conn.commit()
            cur.close()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error upserting customer embedding for {customer_id}: {e}")
            raise

    def batch_upsert_product_embeddings(
        self,
        embeddings: List[Tuple[int, List[float]]],
        model_version_id: int,
        batch_size: int = 500
    ) -> int:
        """
        Batch insert/update product embeddings for better performance
        
        Args:
            embeddings: List of (product_id, embedding) tuples
            model_version_id: Reference to model version
            batch_size: Number of records per batch
        
        Returns:
            Number of embeddings inserted
        """
        if not self.pgvector_enabled:
            logger.warning("pgvector not enabled - skipping batch embedding insert")
            return 0
        
        query = """
            INSERT INTO product_embeddings (product_id, embedding, model_version_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (product_id) 
            DO UPDATE SET 
                embedding = EXCLUDED.embedding,
                model_version_id = EXCLUDED.model_version_id,
                created_at = NOW()
        """
        
        try:
            cur = self.conn.cursor()
            count = 0
            
            for i in range(0, len(embeddings), batch_size):
                batch = embeddings[i:i+batch_size]
                data = [(pid, np.array(emb), model_version_id) for pid, emb in batch]
                cur.executemany(query, data)
                count += len(batch)
                
                if i % (batch_size * 10) == 0 and i > 0:
                    logger.info(f"Batch upserted {i}/{len(embeddings)} product embeddings...")
            
            self.conn.commit()
            cur.close()
            logger.info(f"✓ Batch upserted {count} product embeddings")
            return count
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error batch upserting product embeddings: {e}")
            raise

    def batch_upsert_customer_embeddings(
        self,
        embeddings: List[Tuple[int, List[float]]],
        model_version_id: int,
        batch_size: int = 500
    ) -> int:
        """
        Batch insert/update customer embeddings for better performance
        
        Args:
            embeddings: List of (customer_id, embedding) tuples
            model_version_id: Reference to model version
            batch_size: Number of records per batch
        
        Returns:
            Number of embeddings inserted
        """
        if not self.pgvector_enabled:
            logger.warning("pgvector not enabled - skipping batch embedding insert")
            return 0
        
        query = """
            INSERT INTO customer_embeddings (customer_id, embedding, model_version_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (customer_id) 
            DO UPDATE SET 
                embedding = EXCLUDED.embedding,
                model_version_id = EXCLUDED.model_version_id,
                updated_at = NOW()
        """
        
        try:
            cur = self.conn.cursor()
            count = 0
            
            for i in range(0, len(embeddings), batch_size):
                batch = embeddings[i:i+batch_size]
                data = [(cid, np.array(emb), model_version_id) for cid, emb in batch]
                cur.executemany(query, data)
                count += len(batch)
                
                if i % (batch_size * 10) == 0 and i > 0:
                    logger.info(f"Batch upserted {i}/{len(embeddings)} customer embeddings...")
            
            self.conn.commit()
            cur.close()
            logger.info(f"✓ Batch upserted {count} customer embeddings")
            return count
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error batch upserting customer embeddings: {e}")
            raise

    def get_customer_embedding(self, customer_id: int) -> Optional[np.ndarray]:
        """
        Get embedding for a specific customer
        
        Args:
            customer_id: Customer ID
        
        Returns:
            Embedding as numpy array or None if not found
        """
        if not self.pgvector_enabled:
            return None
        
        query = "SELECT embedding FROM customer_embeddings WHERE customer_id = %s"
        
        try:
            cur = self.conn.cursor()
            cur.execute(query, (customer_id,))
            result = cur.fetchone()
            cur.close()
            
            if result:
                return np.array(result[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching customer embedding for {customer_id}: {e}")
            raise

    def get_product_embedding(self, product_id: int) -> Optional[np.ndarray]:
        """
        Get embedding for a specific product
        
        Args:
            product_id: Product ID
        
        Returns:
            Embedding as numpy array or None if not found
        """
        if not self.pgvector_enabled:
            return None
        
        query = "SELECT embedding FROM product_embeddings WHERE product_id = %s"
        
        try:
            cur = self.conn.cursor()
            cur.execute(query, (product_id,))
            result = cur.fetchone()
            cur.close()
            
            if result:
                return np.array(result[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching product embedding for {product_id}: {e}")
            raise

    def get_similar_customers_pgvector(
        self, 
        customer_id: int, 
        k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find k most similar customers using pgvector ANN search
        
        Args:
            customer_id: Target customer ID
            k: Number of similar customers to return
        
        Returns:
            List of dicts with customer_id and distance
        """
        if not self.pgvector_enabled:
            logger.warning("pgvector not enabled - returning empty list")
            return []
        
        query = """
            SELECT ce2.customer_id, ce1.embedding <-> ce2.embedding AS distance
            FROM customer_embeddings ce1
            CROSS JOIN customer_embeddings ce2
            WHERE ce1.customer_id = %s 
              AND ce2.customer_id != %s
            ORDER BY distance
            LIMIT %s
        """
        
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, (customer_id, customer_id, k))
            results = cur.fetchall()
            cur.close()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error finding similar customers for {customer_id}: {e}")
            raise

    def get_product_embeddings_for_customers(
        self, 
        customer_ids: List[int]
    ) -> Dict[int, List[Tuple[int, np.ndarray]]]:
        """
        Get product embeddings for purchases made by given customers
        
        Args:
            customer_ids: List of customer IDs
        
        Returns:
            Dict mapping customer_id to list of (product_id, embedding) tuples
        """
        if not self.pgvector_enabled or not customer_ids:
            return {}
        
        query = """
            SELECT p.customer_id, p.product_id, pe.embedding
            FROM purchases p
            JOIN product_embeddings pe ON p.product_id = pe.product_id
            WHERE p.customer_id = ANY(%s)
        """
        
        try:
            cur = self.conn.cursor()
            cur.execute(query, (customer_ids,))
            results = cur.fetchall()
            cur.close()
            
            # Group by customer
            customer_products = {}
            for customer_id, product_id, embedding in results:
                if customer_id not in customer_products:
                    customer_products[customer_id] = []
                customer_products[customer_id].append((product_id, np.array(embedding)))
            
            return customer_products
        except Exception as e:
            logger.error(f"Error fetching product embeddings for customers: {e}")
            raise

    def recommend_products_pgvector(
        self, 
        query_embedding: np.ndarray, 
        exclude_product_ids: List[int],
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find top N products nearest to query embedding using pgvector
        
        Args:
            query_embedding: Query vector (normalized)
            exclude_product_ids: Product IDs to exclude from results
            top_n: Number of recommendations to return
        
        Returns:
            List of dicts with product_id and distance
        """
        if not self.pgvector_enabled:
            logger.warning("pgvector not enabled - returning empty list")
            return []
        
        # Handle empty exclusion list
        if not exclude_product_ids:
            query = """
                SELECT product_id, embedding <-> %s AS distance
                FROM product_embeddings
                ORDER BY distance
                LIMIT %s
            """
            params = (query_embedding, top_n)
        else:
            query = """
                SELECT product_id, embedding <-> %s AS distance
                FROM product_embeddings
                WHERE product_id != ALL(%s)
                ORDER BY distance
                LIMIT %s
            """
            params = (query_embedding, exclude_product_ids, top_n)
        
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params)
            results = cur.fetchall()
            cur.close()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error recommending products via pgvector: {e}")
            raise

    def get_product_embeddings_by_ids(
        self, 
        product_ids: List[int]
    ) -> Dict[int, np.ndarray]:
        """
        Get embeddings for specific products
        
        Args:
            product_ids: List of product IDs
        
        Returns:
            Dict mapping product_id to embedding array
        """
        if not self.pgvector_enabled or not product_ids:
            return {}
        
        query = """
            SELECT product_id, embedding
            FROM product_embeddings
            WHERE product_id = ANY(%s)
        """
        
        try:
            cur = self.conn.cursor()
            cur.execute(query, (product_ids,))
            results = cur.fetchall()
            cur.close()
            
            return {product_id: np.array(embedding) for product_id, embedding in results}
        except Exception as e:
            logger.error(f"Error fetching product embeddings by IDs: {e}")
            raise

    def get_customer_purchased_product_ids(self, customer_id: int) -> List[int]:
        """
        Get list of product IDs purchased by a customer
        
        Args:
            customer_id: Customer ID
        
        Returns:
            List of product IDs
        """
        query = """
            SELECT DISTINCT product_id
            FROM purchases
            WHERE customer_id = %s
        """
        
        try:
            cur = self.conn.cursor()
            cur.execute(query, (customer_id,))
            results = cur.fetchall()
            cur.close()
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error fetching purchased products for customer {customer_id}: {e}")
            raise

    def get_all_customers_with_purchases(self) -> List[int]:
        """
        Get all customer IDs that have at least one purchase
        
        Returns:
            List of customer IDs
        """
        query = """
            SELECT DISTINCT customer_id
            FROM purchases
            ORDER BY customer_id
        """
        
        try:
            cur = self.conn.cursor()
            cur.execute(query)
            results = cur.fetchall()
            cur.close()
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error fetching customers with purchases: {e}")
            raise

    def count_embeddings(self) -> Dict[str, int]:
        """
        Get counts of stored embeddings
        
        Returns:
            Dict with counts for products and customers
        """
        try:
            cur = self.conn.cursor()
            
            cur.execute("SELECT COUNT(*) FROM product_embeddings")
            product_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM customer_embeddings")
            customer_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM model_versions")
            model_count = cur.fetchone()[0]
            
            cur.close()
            
            return {
                'products': product_count,
                'customers': customer_count,
                'model_versions': model_count
            }
        except Exception as e:
            logger.error(f"Error counting embeddings: {e}")
            return {'products': 0, 'customers': 0, 'model_versions': 0}
