import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Optional
import logging

from app.services.database import DatabaseService

logger = logging.getLogger(__name__)

class ContentBasedRecommender:
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.product_features = None
        self.product_similarity_matrix = None
        self.product_ids = None
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2)
        )
        logger.info("Content-based recommender initialized")
    
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
    
    def compute_similarity(self):
        try:
            logger.info("Computing product similarity using TF-IDF...")
            
            if self.product_features is None:
                raise ValueError("Data not loaded. Call load_data() first.")
            
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(
                self.product_features['content']
            )
            
            self.product_similarity_matrix = cosine_similarity(tfidf_matrix)
            
            np.fill_diagonal(self.product_similarity_matrix, 0)
            
            logger.info("✓ Product similarity matrix computed")
            
        except Exception as e:
            logger.error(f"Error computing product similarity: {e}")
            raise
    
    def get_recommendations(
        self,
        customer_id: int,
        top_n: int = 5,
        min_similarity: float = 0.1
    ) -> List[Dict[str, Any]]:
        try:
            purchased_products = self.db.get_customer_purchases(customer_id)
            
            if not purchased_products:
                logger.warning(f"No purchase history for customer {customer_id}")
                return self._get_popular_items(top_n)
            
            purchased_product_ids = [p['product_id'] for p in purchased_products]
            
            candidate_scores = {}
            
            for product_id in purchased_product_ids:
                if product_id not in self.product_ids:
                    continue
                
                product_idx = self.product_ids.index(product_id)
                similarities = self.product_similarity_matrix[product_idx]
                
                for idx, similarity in enumerate(similarities):
                    candidate_product_id = self.product_ids[idx]
                    
                    if candidate_product_id in purchased_product_ids:
                        continue
                    
                    if similarity < min_similarity:
                        continue
                    
                    if candidate_product_id not in candidate_scores:
                        candidate_scores[candidate_product_id] = 0
                    candidate_scores[candidate_product_id] += similarity
            
            if not candidate_scores:
                logger.warning(f"No similar products found for customer {customer_id}")
                return self._get_popular_items(top_n)
            
            sorted_products = sorted(
                candidate_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]
            
            recommendations = []
            for product_id, score in sorted_products:
                product_info = self.product_features[
                    self.product_features['product_id'] == product_id
                ].iloc[0]
                
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
        try:
            if product_id not in self.product_ids:
                logger.warning(f"Product {product_id} not found")
                return []
            
            product_idx = self.product_ids.index(product_id)
            similarities = self.product_similarity_matrix[product_idx]
            
            top_indices = np.argsort(similarities)[::-1][:top_n]
            
            recommendations = []
            for idx in top_indices:
                similar_product_id = self.product_ids[idx]
                similarity_score = similarities[idx]
                
                if similarity_score < 0.1:
                    continue
                
                product_info = self.product_features[
                    self.product_features['product_id'] == similar_product_id
                ].iloc[0]
                
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
