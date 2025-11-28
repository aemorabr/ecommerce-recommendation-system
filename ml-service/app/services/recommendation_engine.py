"""
Recommendation Engine using Collaborative Filtering
Implements customer similarity analysis and product recommendations
"""

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.services.database import DatabaseService

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """
    Collaborative filtering recommendation engine.
    Uses customer-customer similarity based on purchase patterns.
    """

    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.user_item_matrix = None
        self.customer_ids = None
        self.product_ids = None
        self.current_model_version_id = None
        self.last_trained = None
        self.scaler = StandardScaler()

        logger.info("Recommendation engine initialized (pgvector-backed)")

    def load_data(self):
        """Load purchase data and create user-item matrix"""
        try:
            logger.info("Loading purchase data...")

            # Get purchase data
            purchases = self.db.get_purchase_matrix()

            if not purchases:
                raise ValueError("No purchase data available")

            # Convert to DataFrame
            df = pd.DataFrame(purchases)

            # Create user-item matrix (customers x products)
            self.user_item_matrix = df.pivot_table(
                index='customer_id',
                columns='product_id',
                values='quantity',
                fill_value=0
            )

            # Store customer and product IDs
            self.customer_ids = self.user_item_matrix.index.tolist()
            self.product_ids = self.user_item_matrix.columns.tolist()

            logger.info(f"Loaded matrix: {len(self.customer_ids)} customers x {len(self.product_ids)} products")
            logger.info(f"Matrix sparsity: {self._calculate_sparsity():.2%}")

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise

    def compute_similarity(self, model_version_id: int):
        """
        Compute customer embeddings and store directly to database.
        Uses normalized user-item vectors as customer embeddings.
        
        Args:
            model_version_id: ID of the model version to associate embeddings with
        """
        try:
            logger.info("Computing customer embeddings from purchase patterns...")

            if self.user_item_matrix is None:
                raise ValueError("Data not loaded. Call load_data() first.")
            
            if not self.db.pgvector_enabled:
                raise RuntimeError("pgvector is required but not enabled")

            # Normalize user-item matrix to create customer embeddings
            from sklearn.preprocessing import normalize
            import numpy as np
            
            embeddings_list = []
            target_dim = 128  # Match database vector dimension
            
            for idx, customer_id in enumerate(self.customer_ids):
                # Get customer's purchase vector
                customer_vector = self.user_item_matrix.iloc[idx].values
                
                # Pad to exactly 128 dimensions if needed
                actual_dim = len(customer_vector)
                if actual_dim < target_dim:
                    padding = np.zeros(target_dim - actual_dim)
                    customer_vector = np.hstack([customer_vector, padding])
                elif actual_dim > target_dim:
                    customer_vector = customer_vector[:target_dim]
                
                # Normalize to unit L2 norm
                customer_embedding = normalize(
                    customer_vector.reshape(1, -1),
                    norm='l2'
                )[0]
                
                embeddings_list.append((customer_id, customer_embedding.tolist()))
            
            # Batch insert to database
            count = self.db.batch_upsert_customer_embeddings(
                embeddings_list,
                model_version_id
            )
            
            self.current_model_version_id = model_version_id
            self.last_trained = datetime.now()

            logger.info(f"✓ Computed and stored {count} customer embeddings to database")

        except Exception as e:
            logger.error(f"Error computing customer embeddings: {e}")
            raise

    def get_recommendations(
        self,
        customer_id: int,
        top_n: int = 5,
        similarity_threshold: float = 0.1,
        k_similar_customers: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get product recommendations using pgvector-backed collaborative filtering.
        
        Workflow:
        1. Get customer embedding from database
        2. Find k similar customers via ANN search
        3. Get products purchased by similar customers
        4. Aggregate and rank products
        5. Exclude already-purchased items
        
        Args:
            customer_id: Customer ID
            top_n: Number of recommendations to return
            similarity_threshold: Minimum similarity score (not used with pgvector distance)
            k_similar_customers: Number of similar customers to consider

        Returns:
            List of recommendations with product_id, score, and reason
        """
        try:
            if not self.db.pgvector_enabled:
                raise RuntimeError("pgvector is required but not enabled")
            
            # Get customer embedding from database
            customer_embedding = self.db.get_customer_embedding(customer_id)
            
            if customer_embedding is None:
                logger.warning(f"No embedding found for customer {customer_id}, returning popular items")
                return self._get_popular_items(top_n)

            # Find similar customers via pgvector ANN search
            similar_customers = self.db.get_similar_customers_pgvector(
                customer_id,
                k=k_similar_customers
            )

            if not similar_customers:
                logger.warning(f"No similar customers found for {customer_id}")
                return self._get_popular_items(top_n)

            # Get products purchased by similar customers with weighted scores
            similar_customer_ids = [c['customer_id'] for c in similar_customers]
            
            # Query purchases for similar customers
            query = """
                SELECT p.product_id, SUM(p.quantity) as total_quantity
                FROM purchases p
                WHERE p.customer_id = ANY(%s)
                GROUP BY p.product_id
            """
            
            cur = self.db.conn.cursor()
            cur.execute(query, (similar_customer_ids,))
            purchase_results = cur.fetchall()
            cur.close()
            
            # Get products current customer has already purchased (for exclusion)
            exclude_products = self.db.get_customer_purchased_product_ids(customer_id)
            
            # Calculate scores weighted by customer similarity
            product_scores = {}
            similarity_map = {c['customer_id']: c['distance'] for c in similar_customers}
            
            # Get who bought what
            purchase_by_customer_query = """
                SELECT customer_id, product_id, SUM(quantity) as quantity
                FROM purchases
                WHERE customer_id = ANY(%s)
                GROUP BY customer_id, product_id
            """
            
            cur = self.db.conn.cursor()
            cur.execute(purchase_by_customer_query, (similar_customer_ids,))
            customer_purchases = cur.fetchall()
            cur.close()
            
            for cust_id, prod_id, quantity in customer_purchases:
                if prod_id in exclude_products:
                    continue
                
                distance = similarity_map.get(cust_id, 1.0)
                # Weight by inverse distance (smaller distance = higher weight)
                similarity_weight = 1.0 / (distance + 0.001)
                
                if prod_id not in product_scores:
                    product_scores[prod_id] = 0
                product_scores[prod_id] += similarity_weight * quantity

            if not product_scores:
                logger.warning(f"No recommendations found for customer {customer_id} after filtering")
                return self._get_popular_items(top_n)

            # Sort by score and get top N
            sorted_products = sorted(
                product_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]

            # Fetch product details
            all_products = self.db.get_all_products()
            product_map = {p['product_id']: p for p in all_products}

            # Build recommendations
            recommendations = []
            for product_id, score in sorted_products:
                product_info = product_map.get(product_id, {})

                recommendations.append({
                    'product_id': int(product_id),
                    'score': float(score),
                    'reason': 'customers_like_you',
                    'name': product_info.get('name', ''),
                    'category': product_info.get('category', ''),
                    'price': float(product_info.get('price', 0.0))
                })

            # If we don't have enough recommendations, fill with popular items
            if len(recommendations) < top_n:
                popular = self._get_popular_items(top_n - len(recommendations))
                recommended_ids = {r['product_id'] for r in recommendations}
                for item in popular:
                    if item['product_id'] not in recommended_ids and item['product_id'] not in exclude_products:
                        recommendations.append(item)

            return recommendations[:top_n]

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            raise

    def get_similar_customers(
        self,
        customer_id: int,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find customers with similar purchase patterns using pgvector.

        Args:
            customer_id: Customer ID
            top_n: Number of similar customers to return

        Returns:
            List of similar customers with similarity scores
        """
        try:
            if not self.db.pgvector_enabled:
                raise RuntimeError("pgvector is required but not enabled")
            
            # Use pgvector to find similar customers
            similar_customers = self.db.get_similar_customers_pgvector(
                customer_id,
                k=top_n
            )
            
            if not similar_customers:
                logger.warning(f"No similar customers found for {customer_id}")
                return []
            
            # Convert distance to similarity score
            result = []
            for customer in similar_customers:
                distance = customer['distance']
                # Convert L2 distance to similarity (0 = identical, 2 = opposite for normalized vectors)
                similarity_score = max(0, 1 - (distance / 2))
                
                result.append({
                    'customer_id': int(customer['customer_id']),
                    'similarity_score': float(similarity_score),
                    'distance': float(distance)
                })
            
            return result

        except Exception as e:
            logger.error(f"Error finding similar customers: {e}")
            raise

    def _get_popular_items(self, top_n: int) -> List[Dict[str, Any]]:
        """
        Fallback: return popular items for new/cold-start customers.

        Args:
            top_n: Number of items to return

        Returns:
            List of popular products
        """
        try:
            popular = self.db.get_popular_products(limit=top_n)

            all_products = self.db.get_all_products()
            product_map = {p['product_id']: p for p in all_products}

            recommendations = []
            for item in popular:
                product_id = int(item['product_id'])
                product_info = product_map.get(product_id, {})

                recommendations.append({
                    'product_id': product_id,
                    'score': float(item['purchase_count']),
                    'reason': 'popular',
                    'name': product_info.get('name', ''),
                    'category': product_info.get('category', ''),
                    'price': float(product_info.get('price', 0.0))
                })

            return recommendations

        except Exception as e:
            logger.error(f"Error getting popular items: {e}")
            return []

    def _calculate_sparsity(self) -> float:
        """Calculate sparsity of user-item matrix"""
        if self.user_item_matrix is None:
            return 0.0

        total_elements = self.user_item_matrix.size
        non_zero_elements = np.count_nonzero(self.user_item_matrix.values)
        sparsity = 1 - (non_zero_elements / total_elements)

        return sparsity

    def is_ready(self) -> bool:
        """Check if model is trained and ready"""
        return (
            self.user_item_matrix is not None and
            self.current_model_version_id is not None
        )

    def get_customer_count(self) -> int:
        """Get number of customers in the model"""
        return len(self.customer_ids) if self.customer_ids else 0

    def get_product_count(self) -> int:
        """Get number of products in the model"""
        return len(self.product_ids) if self.product_ids else 0

    def get_metrics(self) -> Dict[str, Any]:
        """Get model performance metrics"""
        try:
            total_customers = self.db.get_total_customers()
            total_products = self.db.get_total_products()
            total_purchases = self.db.get_total_purchases()

            avg_purchases = (
                total_purchases / total_customers
                if total_customers > 0 else 0
            )

            return {
                'total_customers': total_customers,
                'total_products': total_products,
                'total_purchases': total_purchases,
                'avg_purchases_per_customer': round(avg_purchases, 2),
                'model_last_trained': self.last_trained,
                'sparsity': round(self._calculate_sparsity(), 4)
            }

        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """Get the dimension of customer embeddings (number of products)"""
        if self.product_ids:
            return len(self.product_ids)
        return 0
