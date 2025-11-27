"""
Quick test script to verify database connection and data
Run this before starting the ML service to ensure everything is set up correctly
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_database_connection():
    """Test if we can connect to the database"""
    print("Testing database connection...")
    
    try:
        from app.services.database import DatabaseService
        db = DatabaseService()
        
        if db.check_connection():
            print("✓ Database connection successful!")
            return True
        else:
            print("✗ Database connection failed!")
            return False
    except Exception as e:
        print(f"✗ Error connecting to database: {e}")
        return False

def test_data_exists():
    """Test if sample data exists in the database"""
    print("\nChecking for sample data...")
    
    try:
        from app.services.database import DatabaseService
        db = DatabaseService()
        
        # Check products
        products = db.get_all_products()
        print(f"✓ Found {len(products)} products")
        
        # Check customers
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        print(f"✓ Found {customer_count} customers")
        
        # Check purchases
        cursor.execute("SELECT COUNT(*) FROM purchases")
        purchase_count = cursor.fetchone()[0]
        print(f"✓ Found {purchase_count} purchases")
        
        cursor.close()
        conn.close()
        
        if len(products) == 0 or customer_count == 0 or purchase_count == 0:
            print("\n⚠ Warning: Database is empty! Run generate_sample_data.py")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error checking data: {e}")
        return False

def test_imports():
    """Test if all required modules can be imported"""
    print("\nTesting Python dependencies...")
    
    required_modules = [
        'fastapi',
        'uvicorn',
        'sklearn',
        'pandas',
        'numpy',
        'psycopg2'
    ]
    
    all_ok = True
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            print(f"✗ {module} - NOT INSTALLED")
            all_ok = False
    
    return all_ok

def main():
    print("="*60)
    print("E-Commerce Recommendation System - Pre-flight Check")
    print("="*60)
    print()
    
    # Test imports
    imports_ok = test_imports()
    
    if not imports_ok:
        print("\n" + "="*60)
        print("FAILED: Missing dependencies")
        print("="*60)
        print("\nRun: pip install -r requirements.txt")
        return False
    
    # Test database connection
    connection_ok = test_database_connection()
    
    if not connection_ok:
        print("\n" + "="*60)
        print("FAILED: Cannot connect to database")
        print("="*60)
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. Database 'ecommerce' exists")
        print("3. .env file has correct credentials")
        return False
    
    # Test data exists
    data_ok = test_data_exists()
    
    print("\n" + "="*60)
    if connection_ok and data_ok and imports_ok:
        print("SUCCESS: All checks passed!")
        print("="*60)
        print("\nYou can now start the ML service:")
        print("  uvicorn app.main:app --reload --port 8000")
        return True
    else:
        print("FAILED: Some checks did not pass")
        print("="*60)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
