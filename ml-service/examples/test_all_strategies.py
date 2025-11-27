import requests
import json
from typing import List, Dict

BASE_URL = "http://localhost:8000"

def print_recommendations(recommendations: List[Dict], strategy: str):
    print(f"\n{'='*60}")
    print(f"Strategy: {strategy.upper()}")
    print(f"{'='*60}")
    
    if not recommendations:
        print("No recommendations found")
        return
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec.get('name', 'Unknown Product')}")
        print(f"   Product ID: {rec['product_id']}")
        print(f"   Category: {rec.get('category', 'N/A')}")
        print(f"   Price: ${rec.get('price', 0):.2f}")
        print(f"   Score: {rec['score']:.4f}")
        print(f"   Reason: {rec['reason']}")

def test_all_strategies(customer_id: int = 1, limit: int = 5):
    strategies = ['cf', 'content', 'hybrid', 'popular']
    
    print(f"\n{'#'*60}")
    print(f"Testing All Recommendation Strategies")
    print(f"Customer ID: {customer_id} | Limit: {limit}")
    print(f"{'#'*60}")
    
    for strategy in strategies:
        try:
            response = requests.get(
                f"{BASE_URL}/recommendations/{customer_id}",
                params={'strategy': strategy, 'limit': limit}
            )
            
            if response.status_code == 200:
                recommendations = response.json()
                print_recommendations(recommendations, strategy)
            else:
                print(f"\n❌ Error for {strategy}: {response.status_code}")
                print(f"   {response.text}")
        
        except Exception as e:
            print(f"\n❌ Exception for {strategy}: {str(e)}")

def test_similar_products(product_id: int = 1, limit: int = 5):
    print(f"\n{'='*60}")
    print(f"Similar Products for Product ID: {product_id}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/similar-products/{product_id}",
            params={'limit': limit}
        )
        
        if response.status_code == 200:
            similar = response.json()
            print_recommendations(similar, "similar_products")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def test_similar_customers(customer_id: int = 1, limit: int = 5):
    print(f"\n{'='*60}")
    print(f"Similar Customers for Customer ID: {customer_id}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/similar-customers/{customer_id}",
            params={'limit': limit}
        )
        
        if response.status_code == 200:
            similar = response.json()
            for i, customer in enumerate(similar, 1):
                print(f"\n{i}. Customer ID: {customer['customer_id']}")
                print(f"   Similarity Score: {customer['similarity_score']:.4f}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def test_health_check():
    print(f"\n{'='*60}")
    print(f"Health Check")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            health = response.json()
            print(f"\nStatus: {health['status']}")
            print(f"Database Connected: {health['database_connected']}")
            print(f"Model Loaded: {health['model_loaded']}")
        else:
            print(f"❌ Error: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def test_metrics():
    print(f"\n{'='*60}")
    print(f"System Metrics")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{BASE_URL}/metrics")
        
        if response.status_code == 200:
            metrics = response.json()
            print(f"\nTotal Customers: {metrics['total_customers']}")
            print(f"Total Products: {metrics['total_products']}")
            print(f"Total Purchases: {metrics['total_purchases']}")
            print(f"Avg Purchases/Customer: {metrics['avg_purchases_per_customer']:.2f}")
            print(f"Matrix Sparsity: {metrics['sparsity']:.2%}")
            print(f"Last Trained: {metrics.get('model_last_trained', 'N/A')}")
        else:
            print(f"❌ Error: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def compare_strategies(customer_id: int = 1):
    print(f"\n{'#'*60}")
    print(f"Strategy Comparison for Customer {customer_id}")
    print(f"{'#'*60}")
    
    strategies = ['cf', 'content', 'hybrid']
    results = {}
    
    for strategy in strategies:
        try:
            response = requests.get(
                f"{BASE_URL}/recommendations/{customer_id}",
                params={'strategy': strategy, 'limit': 3}
            )
            
            if response.status_code == 200:
                results[strategy] = response.json()
        except Exception as e:
            print(f"Error fetching {strategy}: {e}")
    
    print(f"\n{'Strategy':<15} {'Product IDs':<30} {'Avg Score':<10}")
    print("-" * 60)
    
    for strategy, recs in results.items():
        product_ids = [str(r['product_id']) for r in recs]
        avg_score = sum(r['score'] for r in recs) / len(recs) if recs else 0
        print(f"{strategy:<15} {', '.join(product_ids):<30} {avg_score:.4f}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("E-Commerce Hybrid Recommendation System - API Test Suite")
    print("="*60)
    
    test_health_check()
    
    test_metrics()
    
    test_all_strategies(customer_id=1, limit=5)
    
    test_similar_customers(customer_id=1, limit=5)
    
    test_similar_products(product_id=1, limit=5)
    
    compare_strategies(customer_id=1)
    
    print("\n" + "="*60)
    print("Test Suite Complete!")
    print("="*60 + "\n")
