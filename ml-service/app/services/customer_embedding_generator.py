"""
Customer Embedding Generator
Generates customer preference embeddings by aggregating product embeddings
"""

import numpy as np
from sklearn.preprocessing import normalize
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict

from app.services.database import DatabaseService

logger = logging.getLogger(__name__)


class CustomerEmbeddingGenerator:
    """
    Generate customer embeddings by aggregating purchased product embeddings.
    Supports weighted averaging by recency or quantity.
    """

    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        logger.info("Customer embedding generator initialized")

    def generate_and_store_embeddings(
        self,
        model_version_id: int,
        weight_by_quantity: bool = False,
        batch_size: int = 500
    ) -> int:
        """
        Generate customer embeddings and store them in the database
        
        Args:
            model_version_id: Model version to associate embeddings with
            weight_by_quantity: If True, weight products by purchase quantity
            batch_size: Batch size for database inserts
        
        Returns:
            Number of customer embeddings generated
        """
        try:
            logger.info("Generating customer embeddings from purchase history...")
            
            # Get all customers with purchases
            customer_ids = self.db.get_all_customers_with_purchases()
            
            if not customer_ids:
                logger.warning("No customers with purchases found")
                return 0
            
            logger.info(f"Processing {len(customer_ids)} customers...")
            
            customer_embeddings = []
            
            for i, customer_id in enumerate(customer_ids):
                try:
                    embedding = self._generate_customer_embedding(
                        customer_id,
                        weight_by_quantity=weight_by_quantity
                    )
                    
                    if embedding is not None:
                        customer_embeddings.append((customer_id, embedding.tolist()))
                    
                    if (i + 1) % 100 == 0:
                        logger.info(f"Generated embeddings for {i + 1}/{len(customer_ids)} customers...")
                        
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for customer {customer_id}: {e}")
                    continue
            
            # Batch store embeddings
            if customer_embeddings:
                count = self.db.batch_upsert_customer_embeddings(
                    customer_embeddings,
                    model_version_id,
                    batch_size=batch_size
                )
                logger.info(f"✓ Generated and stored {count} customer embeddings")
                return count
            else:
                logger.warning("No customer embeddings were generated")
                return 0
                
        except Exception as e:
            logger.error(f"Error generating customer embeddings: {e}")
            raise

    def _generate_customer_embedding(
        self,
        customer_id: int,
        weight_by_quantity: bool = False
    ) -> Optional[np.ndarray]:
        """
        Generate a single customer embedding by averaging product embeddings
        
        Args:
            customer_id: Customer ID
            weight_by_quantity: Weight products by purchase quantity
        
        Returns:
            Normalized customer embedding or None if no products found
        """
        try:
            # Get customer's purchased products
            if weight_by_quantity:
                purchases = self._get_customer_purchases_with_quantity(customer_id)
                if not purchases:
                    return None
                
                product_ids = [p['product_id'] for p in purchases]
                quantities = [p['quantity'] for p in purchases]
            else:
                product_ids = self.db.get_customer_purchased_product_ids(customer_id)
                if not product_ids:
                    return None
                quantities = [1.0] * len(product_ids)
            
            # Get embeddings for purchased products
            product_embeddings_dict = self.db.get_product_embeddings_by_ids(product_ids)
            
            if not product_embeddings_dict:
                logger.warning(f"No product embeddings found for customer {customer_id}")
                return None
            
            # Compute weighted average
            embeddings = []
            weights = []
            
            for product_id, quantity in zip(product_ids, quantities):
                if product_id in product_embeddings_dict:
                    embeddings.append(product_embeddings_dict[product_id])
                    weights.append(quantity)
            
            if not embeddings:
                return None
            
            # Weighted average
            embeddings_array = np.array(embeddings)
            weights_array = np.array(weights).reshape(-1, 1)
            
            # Normalize weights to sum to 1
            weights_normalized = weights_array / weights_array.sum()
            
            # Compute weighted mean
            customer_embedding = (embeddings_array * weights_normalized).sum(axis=0)
            
            # Normalize to unit L2 norm
            customer_embedding_normalized = normalize(
                customer_embedding.reshape(1, -1),
                norm='l2'
            )[0]
            
            return customer_embedding_normalized
            
        except Exception as e:
            logger.error(f"Error generating embedding for customer {customer_id}: {e}")
            return None

    def _get_customer_purchases_with_quantity(
        self,
        customer_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get customer purchases aggregated by product with total quantity
        
        Args:
            customer_id: Customer ID
        
        Returns:
            List of dicts with product_id and quantity
        """
        query = """
            SELECT product_id, SUM(quantity) as quantity
            FROM purchases
            WHERE customer_id = %s
            GROUP BY product_id
        """
        
        try:
            cur = self.db.conn.cursor()
            cur.execute(query, (customer_id,))
            results = cur.fetchall()
            cur.close()
            
            return [
                {'product_id': row[0], 'quantity': row[1]}
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error fetching purchases with quantity: {e}")
            return []

    def update_customer_embedding(
        self,
        customer_id: int,
        model_version_id: int,
        weight_by_quantity: bool = False
    ) -> bool:
        """
        Update embedding for a single customer (e.g., after new purchase)
        
        Args:
            customer_id: Customer ID
            model_version_id: Model version ID
            weight_by_quantity: Weight products by purchase quantity
        
        Returns:
            True if successful, False otherwise
        """
        try:
            embedding = self._generate_customer_embedding(
                customer_id,
                weight_by_quantity=weight_by_quantity
            )
            
            if embedding is not None:
                self.db.upsert_customer_embedding(
                    customer_id,
                    embedding.tolist(),
                    model_version_id
                )
                logger.info(f"✓ Updated embedding for customer {customer_id}")
                return True
            else:
                logger.warning(f"Could not generate embedding for customer {customer_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating customer embedding: {e}")
            return False

    def get_customer_preference_vector(
        self,
        customer_id: int,
        use_db: bool = True
    ) -> Optional[np.ndarray]:
        """
        Get customer preference vector (from DB or generate on-the-fly)
        
        Args:
            customer_id: Customer ID
            use_db: If True, fetch from database; otherwise generate fresh
        
        Returns:
            Customer embedding or None
        """
        if use_db:
            return self.db.get_customer_embedding(customer_id)
        else:
            return self._generate_customer_embedding(customer_id)
