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
        self.similarity_matrix = None
        self.customer_ids = None
        self.product_ids = None
        self.last_trained = None
        self.scaler = StandardScaler()

        logger.info("Recommendation engine initialized")

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

    def compute_similarity(self):
        """Compute customer-customer similarity matrix"""
        try:
            logger.info("Computing customer similarity...")

            if self.user_item_matrix is None:
                raise ValueError("Data not loaded. Call load_data() first.")

            # Normalize the matrix (important for fair comparison)
            normalized = self.scaler.fit_transform(self.user_item_matrix.values)

            # Compute cosine similarity between customers
            self.similarity_matrix = cosine_similarity(normalized)

            # Set diagonal to 0 (customer is not similar to themselves)
            np.fill_diagonal(self.similarity_matrix, 0)

            self.last_trained = datetime.now()

            logger.info("✓ Similarity matrix computed")

        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            raise

    def get_recommendations(
        self,
        customer_id: int,
        top_n: int = 5,
        similarity_threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Get product recommendations for a customer.

        Args:
            customer_id: Customer ID
            top_n: Number of recommendations to return
            similarity_threshold: Minimum similarity score to consider

        Returns:
            List of recommendations with product_id, score, and reason
        """
        try:
            # Check if customer exists in our data
            if customer_id not in self.customer_ids:
                logger.warning(f"Customer {customer_id} not found, returning popular items")
                return self._get_popular_items(top_n)

            # Get customer index
            customer_idx = self.customer_ids.index(customer_id)

            # Get similarity scores for this customer
            similarities = self.similarity_matrix[customer_idx]

            # Find similar customers (above threshold)
            similar_mask = similarities > similarity_threshold
            similar_indices = np.where(similar_mask)[0]

            if len(similar_indices) == 0:
                logger.warning(f"No similar customers found for {customer_id}")
                return self._get_popular_items(top_n)

            # Get top N similar customers
            top_similar_indices = similar_indices[
                np.argsort(similarities[similar_indices])[::-1][:10]
            ]

            # Get products purchased by similar customers
            similar_purchases = self.user_item_matrix.iloc[top_similar_indices]

            # Get products current customer hasn't purchased
            customer_purchases = self.user_item_matrix.iloc[customer_idx]
            not_purchased_mask = customer_purchases == 0

            # Calculate scores for unpurchased products
            # Score = weighted sum of purchases by similar customers
            scores = np.zeros(len(self.product_ids))

            for idx in top_similar_indices:
                similarity_weight = similarities[idx]
                scores += similar_purchases.iloc[
                    list(top_similar_indices).index(idx)
                ].values * similarity_weight

            # Filter to only unpurchased products
            scores = scores * not_purchased_mask.values

            # Get top N products
            top_product_indices = np.argsort(scores)[::-1][:top_n]

            # Build recommendations
            recommendations = []
            for idx in top_product_indices:
                if scores[idx] > 0:  # Only include products with positive scores
                    recommendations.append({
                        'product_id': int(self.product_ids[idx]),
                        'score': float(scores[idx]),
                        'reason': 'customers_like_you'
                    })

            # If we don't have enough recommendations, fill with popular items
            if len(recommendations) < top_n:
                popular = self._get_popular_items(top_n - len(recommendations))
                # Filter out already recommended products
                recommended_ids = {r['product_id'] for r in recommendations}
                for item in popular:
                    if item['product_id'] not in recommended_ids:
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
        Find customers with similar purchase patterns.

        Args:
            customer_id: Customer ID
            top_n: Number of similar customers to return

        Returns:
            List of similar customers with similarity scores
        """
        try:
            if customer_id not in self.customer_ids:
                raise ValueError(f"Customer {customer_id} not found")

            # Get customer index
            customer_idx = self.customer_ids.index(customer_id)

            # Get similarity scores
            similarities = self.similarity_matrix[customer_idx]

            # Get top N similar customers (excluding self)
            top_indices = np.argsort(similarities)[::-1][:top_n]

            similar_customers = []
            for idx in top_indices:
                if similarities[idx] > 0:  # Only include positive similarities
                    similar_customers.append({
                        'customer_id': int(self.customer_ids[idx]),
                        'similarity_score': float(similarities[idx])
                    })

            return similar_customers

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

            return [
                {
                    'product_id': int(item['product_id']),
                    'score': float(item['purchase_count']),
                    'reason': 'popular'
                }
                for item in popular
            ]

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
            self.similarity_matrix is not None
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
