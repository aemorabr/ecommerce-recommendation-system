"""
Database service for PostgreSQL connections and queries
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import List, Dict, Any
import logging

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
        self._connect()

    def _connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.config)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

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

    def get_customer_purchases(self, customer_id: int) -> List[int]:
        """Get list of product IDs purchased by a customer"""
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
            logger.error(f"Error fetching customer purchases: {e}")
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
