import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import logging

from app.services.database import DatabaseService

logger = logging.getLogger(__name__)

class HybridRecommender:
    
    def __init__(
        self,
        collaborative_recommender,
        content_based_recommender,
        cf_weight: float = 0.6,
        content_weight: float = 0.4
    ):
        self.cf_recommender = collaborative_recommender
        self.content_recommender = content_based_recommender
        self.cf_weight = cf_weight
        self.content_weight = content_weight
        
        if abs(cf_weight + content_weight - 1.0) > 0.01:
            logger.warning(f"Weights don't sum to 1.0: {cf_weight} + {content_weight}")
        
        logger.info(f"Hybrid recommender initialized (CF: {cf_weight}, Content: {content_weight})")
    
    def get_recommendations(
        self,
        customer_id: int,
        top_n: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        try:
            cf_recs = self.cf_recommender.get_recommendations(
                customer_id=customer_id,
                top_n=top_n * 2,
                **kwargs
            )
            
            content_recs = self.content_recommender.get_recommendations(
                customer_id=customer_id,
                top_n=top_n * 2,
                **kwargs
            )
            
            combined_scores = {}
            product_info = {}
            
            for rec in cf_recs:
                product_id = rec['product_id']
                combined_scores[product_id] = rec['score'] * self.cf_weight
                product_info[product_id] = {
                    'name': rec.get('name', ''),
                    'category': rec.get('category', ''),
                    'price': rec.get('price', 0.0)
                }
            
            for rec in content_recs:
                product_id = rec['product_id']
                if product_id in combined_scores:
                    combined_scores[product_id] += rec['score'] * self.content_weight
                else:
                    combined_scores[product_id] = rec['score'] * self.content_weight
                
                if product_id not in product_info:
                    product_info[product_id] = {
                        'name': rec.get('name', ''),
                        'category': rec.get('category', ''),
                        'price': rec.get('price', 0.0)
                    }
            
            sorted_products = sorted(
                combined_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]
            
            recommendations = []
            for product_id, score in sorted_products:
                info = product_info.get(product_id, {})
                recommendations.append({
                    'product_id': int(product_id),
                    'score': float(score),
                    'reason': 'hybrid',
                    'name': info.get('name', ''),
                    'category': info.get('category', ''),
                    'price': float(info.get('price', 0.0))
                })
            
            logger.info(f"Generated {len(recommendations)} hybrid recommendations for customer {customer_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating hybrid recommendations: {e}")
            logger.info("Falling back to collaborative filtering")
            return self.cf_recommender.get_recommendations(customer_id, top_n)
    
    def set_weights(self, cf_weight: float, content_weight: float):
        if abs(cf_weight + content_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {cf_weight} + {content_weight}")
        
        self.cf_weight = cf_weight
        self.content_weight = content_weight
        logger.info(f"Updated weights: CF={cf_weight}, Content={content_weight}")
