import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import Mock, MagicMock
import numpy as np
import pandas as pd

from app.services.content_based_recommender import ContentBasedRecommender
from app.services.hybrid_recommender import HybridRecommender

class TestContentBasedRecommender:
    
    def test_initialization(self):
        mock_db = Mock()
        recommender = ContentBasedRecommender(mock_db)
        
        assert recommender.db == mock_db
        assert recommender.product_features is None
        assert recommender.product_similarity_matrix is None
        assert recommender.tfidf_vectorizer is not None
    
    def test_load_data(self):
        mock_db = Mock()
        mock_db.get_all_products.return_value = [
            {
                'product_id': 1,
                'name': 'Laptop',
                'category': 'Electronics',
                'price': 999.99,
                'description': 'High performance laptop'
            },
            {
                'product_id': 2,
                'name': 'Mouse',
                'category': 'Electronics',
                'price': 29.99,
                'description': 'Wireless mouse'
            }
        ]
        
        recommender = ContentBasedRecommender(mock_db)
        recommender.load_data()
        
        assert recommender.product_features is not None
        assert len(recommender.product_ids) == 2
        assert 'content' in recommender.product_features.columns
    
    def test_compute_similarity(self):
        mock_db = Mock()
        mock_db.get_all_products.return_value = [
            {
                'product_id': 1,
                'name': 'Laptop',
                'category': 'Electronics',
                'price': 999.99,
                'description': 'High performance laptop'
            },
            {
                'product_id': 2,
                'name': 'Mouse',
                'category': 'Electronics',
                'price': 29.99,
                'description': 'Wireless mouse'
            }
        ]
        
        recommender = ContentBasedRecommender(mock_db)
        recommender.load_data()
        recommender.compute_similarity()
        
        assert recommender.product_similarity_matrix is not None
        assert recommender.product_similarity_matrix.shape == (2, 2)
        assert recommender.product_similarity_matrix[0, 0] == 0

class TestHybridRecommender:
    
    def test_initialization(self):
        mock_cf = Mock()
        mock_content = Mock()
        
        hybrid = HybridRecommender(mock_cf, mock_content, cf_weight=0.6, content_weight=0.4)
        
        assert hybrid.cf_recommender == mock_cf
        assert hybrid.content_recommender == mock_content
        assert hybrid.cf_weight == 0.6
        assert hybrid.content_weight == 0.4
    
    def test_get_recommendations(self):
        mock_cf = Mock()
        mock_content = Mock()
        
        mock_cf.get_recommendations.return_value = [
            {'product_id': 1, 'score': 0.9, 'name': 'Product 1', 'category': 'Cat1', 'price': 10.0}
        ]
        mock_content.get_recommendations.return_value = [
            {'product_id': 2, 'score': 0.8, 'name': 'Product 2', 'category': 'Cat2', 'price': 20.0}
        ]
        
        hybrid = HybridRecommender(mock_cf, mock_content)
        recommendations = hybrid.get_recommendations(customer_id=1, top_n=2)
        
        assert len(recommendations) == 2
        assert all('product_id' in rec for rec in recommendations)
        assert all('score' in rec for rec in recommendations)
        assert all('reason' in rec for rec in recommendations)
        assert all(rec['reason'] == 'hybrid' for rec in recommendations)
    
    def test_set_weights(self):
        mock_cf = Mock()
        mock_content = Mock()
        
        hybrid = HybridRecommender(mock_cf, mock_content)
        hybrid.set_weights(0.7, 0.3)
        
        assert hybrid.cf_weight == 0.7
        assert hybrid.content_weight == 0.3
    
    def test_set_weights_invalid(self):
        mock_cf = Mock()
        mock_content = Mock()
        
        hybrid = HybridRecommender(mock_cf, mock_content)
        
        with pytest.raises(ValueError):
            hybrid.set_weights(0.7, 0.4)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
