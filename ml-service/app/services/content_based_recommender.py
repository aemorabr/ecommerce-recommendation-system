import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from typing import List, Dict, Any, Optional
import logging

from app.services.database import DatabaseService

logger = logging.getLogger(__name__)

class ContentBasedRecommender:
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.product_features = None
        self.product_ids = None
        self.current_model_version_id = None
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=128,  # Match database vector dimension
            stop_words='english',
            ngram_range=(1, 2)
        )
        logger.info("Content-based recommender initialized (pgvector-backed)")
    
    def load_data(self):
        try:
            logger.info("Loading product data for content-based filtering...")
            
            products = self.db.get_all_products()
            
            if not products:
                raise ValueError("No product data available")
            
            df = pd.DataFrame(products)
            
            df['content'] = (
                df['name'].fillna('') + ' ' +
                df['category'].fillna('') + ' ' +
                df['description'].fillna('')
            )
            
            self.product_features = df[['product_id', 'name', 'category', 'price', 'content']]
            self.product_ids = df['product_id'].tolist()
            
            logger.info(f"Loaded {len(self.product_ids)} products for content-based filtering")
            
        except Exception as e:
            logger.error(f"Error loading product data: {e}")
            raise
    
    def compute_similarity(self, model_version_id: int):
        """
        Compute product embeddings and store directly to database.
        No in-memory similarity matrix is kept.
        
        Args:
            model_version_id: ID of the model version to associate embeddings with
        """
        try:
            logger.info("Computing product embeddings using TF-IDF...")
            
            if self.product_features is None:
                raise ValueError("Data not loaded. Call load_data() first.")
            
            if not self.db.pgvector_enabled:
                raise RuntimeError("pgvector is required but not enabled")
            
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(
                self.product_features['content']
            )
            
            # Normalize embeddings to unit L2 norm for cosine similarity via L2 distance
            tfidf_dense = tfidf_matrix.toarray()
            
            # Pad to exactly 128 dimensions if needed (TF-IDF may create fewer features)
            target_dim = 128
            actual_dim = tfidf_dense.shape[1]
            if actual_dim < target_dim:
                logger.info(f"Padding embeddings from {actual_dim} to {target_dim} dimensions")
                padding = np.zeros((tfidf_dense.shape[0], target_dim - actual_dim))
                tfidf_dense = np.hstack([tfidf_dense, padding])
            elif actual_dim > target_dim:
                logger.warning(f"Truncating embeddings from {actual_dim} to {target_dim} dimensions")
                tfidf_dense = tfidf_dense[:, :target_dim]
            
            normalized_embeddings = normalize(tfidf_dense, norm='l2')
            
            # Prepare batch data for database insertion
            embeddings_list = [
                (self.product_ids[idx], normalized_embeddings[idx].tolist())
                for idx in range(len(self.product_ids))
            ]
            
            # Store directly to database
            count = self.db.batch_upsert_product_embeddings(
                embeddings_list,
                model_version_id
            )
            
            self.current_model_version_id = model_version_id
            
            logger.info(f"✓ Computed and stored {count} product embeddings to database")
            
        except Exception as e:
            logger.error(f"Error computing product embeddings: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """Get the dimension of product embeddings"""
        # TF-IDF max_features determines dimension
        return self.tfidf_vectorizer.max_features if hasattr(self.tfidf_vectorizer, 'max_features') else 500
    
    def get_recommendations(
        self,
        customer_id: int,
        top_n: int = 5,
        min_similarity: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Get content-based recommendations using pgvector similarity search.
        
        For each product the customer purchased, find similar products via
        database vector similarity, then aggregate and rank.
        """
        try:
            if not self.db.pgvector_enabled:
                raise RuntimeError("pgvector is required but not enabled")
            
            purchased_products = self.db.get_customer_purchases(customer_id)
            
            if not purchased_products:
                logger.warning(f"No purchase history for customer {customer_id}")
                return self._get_popular_items(top_n)
            
            purchased_product_ids = [p['product_id'] for p in purchased_products]
            
            # Get embeddings for purchased products from database
            purchased_embeddings = self.db.get_product_embeddings_by_ids(purchased_product_ids)
            
            if not purchased_embeddings:
                logger.warning(f"No embeddings found for customer {customer_id}'s purchases")
                return self._get_popular_items(top_n)
            
            # For each purchased product, find similar products via pgvector
            candidate_scores = {}
            
            for product_id, embedding in purchased_embeddings.items():
                # Query database for similar products
                similar_products = self.db.recommend_products_pgvector(
                    query_embedding=embedding,
                    exclude_product_ids=purchased_product_ids,
                    top_n=20  # Get more candidates for aggregation
                )
                
                # Aggregate similarity scores
                for similar in similar_products:
                    similar_product_id = similar['product_id']
                    distance = similar['distance']
                    
                    # Convert L2 distance to similarity (0 = identical, 2 = opposite for normalized vectors)
                    similarity = max(0, 1 - (distance / 2))
                    
                    if similarity < min_similarity:
                        continue
                    
                    if similar_product_id not in candidate_scores:
                        candidate_scores[similar_product_id] = 0
                    candidate_scores[similar_product_id] += similarity
            
            if not candidate_scores:
                logger.warning(f"No similar products found for customer {customer_id}")
                return self._get_popular_items(top_n)
            
            # Sort by aggregated score
            sorted_products = sorted(
                candidate_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]
            
            # Fetch product details
            product_ids_to_fetch = [pid for pid, _ in sorted_products]
            all_products = self.db.get_all_products()
            product_map = {p['product_id']: p for p in all_products}
            
            recommendations = []
            for product_id, score in sorted_products:
                product_info = product_map.get(product_id)
                
                if product_info:
                    recommendations.append({
                        'product_id': int(product_id),
                        'score': float(score),
                        'reason': 'content_based',
                        'name': product_info['name'],
                        'category': product_info['category'],
                        'price': float(product_info['price'])
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating content-based recommendations: {e}")
            raise
    
    def _get_popular_items(self, top_n: int = 5) -> List[Dict[str, Any]]:
        try:
            popular = self.db.get_popular_products(limit=top_n)
            
            recommendations = []
            for item in popular:
                product_info = self.product_features[
                    self.product_features['product_id'] == item['product_id']
                ].iloc[0] if self.product_features is not None else None
                
                rec = {
                    'product_id': item['product_id'],
                    'score': float(item.get('purchase_count', 0)),
                    'reason': 'popular',
                }
                
                if product_info is not None:
                    rec.update({
                        'name': product_info['name'],
                        'category': product_info['category'],
                        'price': float(product_info['price'])
                    })
                
                recommendations.append(rec)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting popular items: {e}")
            return []
    
    def get_similar_products(
        self,
        product_id: int,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar products using pgvector similarity search.
        
        Args:
            product_id: Source product ID
            top_n: Number of similar products to return
        
        Returns:
            List of similar products with scores
        """
        try:
            if not self.db.pgvector_enabled:
                raise RuntimeError("pgvector is required but not enabled")
            
            # Get the product's embedding from database
            product_embedding = self.db.get_product_embedding(product_id)
            
            if product_embedding is None:
                logger.warning(f"Product {product_id} has no embedding")
                return []
            
            # Query database for similar products
            similar_products = self.db.recommend_products_pgvector(
                query_embedding=product_embedding,
                exclude_product_ids=[product_id],  # Exclude self
                top_n=top_n
            )
            
            if not similar_products:
                return []
            
            # Fetch product details
            all_products = self.db.get_all_products()
            product_map = {p['product_id']: p for p in all_products}
            
            recommendations = []
            for similar in similar_products:
                similar_product_id = similar['product_id']
                distance = similar['distance']
                
                # Convert distance to similarity score
                similarity_score = max(0, 1 - (distance / 2))
                
                if similarity_score < 0.1:
                    continue
                
                product_info = product_map.get(similar_product_id)
                
                if product_info:
                    recommendations.append({
                        'product_id': int(similar_product_id),
                        'score': float(similarity_score),
                        'reason': 'similar_product',
                        'name': product_info['name'],
                        'category': product_info['category'],
                        'price': float(product_info['price'])
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error finding similar products: {e}")
            return []
