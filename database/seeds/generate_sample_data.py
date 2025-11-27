#!/usr/bin/env python3
"""
Generate sample e-commerce data for the recommendation system.
Creates realistic purchase patterns for testing and demonstration.
"""

import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

fake = Faker()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'ecommerce'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'port': os.getenv('DB_PORT', '5432')
}

# Product categories and sample names
CATEGORIES = {
    'Electronics': [
        'Wireless Headphones', 'Smart Watch', 'Laptop Stand', 'USB-C Hub',
        'Mechanical Keyboard', 'Gaming Mouse', 'Webcam', 'Portable SSD',
        'Phone Case', 'Screen Protector', 'Bluetooth Speaker', 'Power Bank',
        'HDMI Cable', 'Monitor', 'Tablet', 'E-Reader', 'Fitness Tracker',
        'Wireless Charger', 'Smart Home Hub', 'Security Camera'
    ],
    'Clothing': [
        'Cotton T-Shirt', 'Denim Jeans', 'Running Shoes', 'Hoodie',
        'Dress Shirt', 'Sneakers', 'Winter Jacket', 'Yoga Pants',
        'Baseball Cap', 'Sunglasses', 'Leather Belt', 'Socks Pack',
        'Sports Bra', 'Polo Shirt', 'Cardigan', 'Dress', 'Shorts',
        'Scarf', 'Gloves', 'Backpack'
    ],
    'Books': [
        'Python Programming Guide', 'Machine Learning Basics', 'Mystery Novel',
        'Science Fiction Epic', 'Self-Help Book', 'Cookbook', 'Biography',
        'History Book', 'Fantasy Series', 'Business Strategy', 'Art Book',
        'Travel Guide', 'Poetry Collection', 'Graphic Novel', 'Textbook',
        'Children\'s Book', 'Thriller', 'Romance Novel', 'Philosophy',
        'Technical Manual'
    ],
    'Home & Garden': [
        'Coffee Maker', 'Blender', 'Air Purifier', 'Vacuum Cleaner',
        'Bed Sheets Set', 'Throw Pillows', 'Wall Art', 'Table Lamp',
        'Storage Bins', 'Kitchen Knife Set', 'Cutting Board', 'Cookware Set',
        'Garden Tools', 'Plant Pot', 'Curtains', 'Area Rug', 'Towel Set',
        'Trash Can', 'Laundry Basket', 'Desk Organizer'
    ],
    'Sports': [
        'Yoga Mat', 'Dumbbells', 'Resistance Bands', 'Jump Rope',
        'Water Bottle', 'Gym Bag', 'Tennis Racket', 'Basketball',
        'Soccer Ball', 'Bicycle Helmet', 'Running Belt', 'Foam Roller',
        'Exercise Ball', 'Kettlebell', 'Pull-up Bar', 'Ankle Weights',
        'Sports Watch', 'Compression Socks', 'Swim Goggles', 'Bike Lock'
    ]
}

def connect_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise

def generate_products(conn, num_products=100):
    """Generate sample products"""
    cur = conn.cursor()
    products = []

    print(f"Generating {num_products} products...")

    for category, product_names in CATEGORIES.items():
        for product_name in product_names[:num_products // len(CATEGORIES)]:
            # Generate realistic price based on category
            if category == 'Electronics':
                price = round(random.uniform(29.99, 599.99), 2)
            elif category == 'Clothing':
                price = round(random.uniform(19.99, 149.99), 2)
            elif category == 'Books':
                price = round(random.uniform(9.99, 49.99), 2)
            elif category == 'Home & Garden':
                price = round(random.uniform(14.99, 299.99), 2)
            else:  # Sports
                price = round(random.uniform(12.99, 199.99), 2)

            cur.execute("""
                INSERT INTO products (name, category, price, description, image_url, stock_quantity)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING product_id
            """, (
                product_name,
                category,
                price,
                fake.text(max_nb_chars=200),
                f"https://picsum.photos/seed/{product_name.replace(' ', '')}/400/400",
                random.randint(10, 500)
            ))

            product_id = cur.fetchone()[0]
            products.append({
                'id': product_id,
                'category': category,
                'price': price
            })

    conn.commit()
    print(f"✓ Created {len(products)} products")
    return products

def generate_customers(conn, num_customers=500):
    """Generate sample customers"""
    cur = conn.cursor()
    customers = []

    print(f"Generating {num_customers} customers...")

    for i in range(num_customers):
        cur.execute("""
            INSERT INTO customers (email, name, created_at, last_login, is_active)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING customer_id
        """, (
            fake.email(),
            fake.name(),
            fake.date_time_between(start_date='-2y', end_date='-1m'),
            fake.date_time_between(start_date='-30d', end_date='now') if random.random() > 0.2 else None,
            random.random() > 0.1  # 90% active
        ))

        customer_id = cur.fetchone()[0]
        customers.append(customer_id)

    conn.commit()
    print(f"✓ Created {len(customers)} customers")
    return customers

def generate_purchases(conn, customers, products):
    """Generate realistic purchase patterns"""
    cur = conn.cursor()
    total_purchases = 0

    print(f"Generating purchase history...")

    # Create customer segments with different behaviors
    for customer_id in customers:
        # Determine customer type
        customer_type = random.choices(
            ['heavy', 'regular', 'light', 'one-time'],
            weights=[0.1, 0.3, 0.4, 0.2]
        )[0]

        if customer_type == 'heavy':
            num_purchases = random.randint(15, 40)
        elif customer_type == 'regular':
            num_purchases = random.randint(5, 15)
        elif customer_type == 'light':
            num_purchases = random.randint(2, 5)
        else:  # one-time
            num_purchases = 1

        # Pick a favorite category (70% of purchases from this category)
        favorite_category = random.choice(list(CATEGORIES.keys()))

        for _ in range(num_purchases):
            # 70% chance to buy from favorite category
            if random.random() < 0.7:
                category_products = [p for p in products if p['category'] == favorite_category]
            else:
                category_products = products

            product = random.choice(category_products)
            quantity = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]

            # Generate purchase date (more recent = more likely)
            days_ago = int(random.expovariate(1/90))  # Exponential distribution
            days_ago = min(days_ago, 365)  # Cap at 1 year
            purchase_date = datetime.now() - timedelta(days=days_ago)

            total_amount = product['price'] * quantity

            cur.execute("""
                INSERT INTO purchases (customer_id, product_id, quantity, purchase_date, total_amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                customer_id,
                product['id'],
                quantity,
                purchase_date,
                total_amount
            ))

            total_purchases += 1

    conn.commit()
    print(f"✓ Created {total_purchases} purchases")
    return total_purchases

def refresh_features(conn):
    """Refresh customer features"""
    cur = conn.cursor()
    print("Refreshing customer features...")
    cur.execute("SELECT refresh_customer_features()")
    conn.commit()
    print("✓ Customer features refreshed")

def print_statistics(conn):
    """Print database statistics"""
    cur = conn.cursor()

    print("\n" + "="*50)
    print("DATABASE STATISTICS")
    print("="*50)

    # Products by category
    cur.execute("""
        SELECT category, COUNT(*) as count
        FROM products
        GROUP BY category
        ORDER BY count DESC
    """)
    print("\nProducts by Category:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    # Customer statistics
    cur.execute("SELECT COUNT(*) FROM customers")
    print(f"\nTotal Customers: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM purchases")
    print(f"Total Purchases: {cur.fetchone()[0]}")

    # Purchase distribution
    cur.execute("""
        SELECT 
            CASE 
                WHEN purchase_count >= 15 THEN 'Heavy (15+)'
                WHEN purchase_count >= 5 THEN 'Regular (5-14)'
                WHEN purchase_count >= 2 THEN 'Light (2-4)'
                ELSE 'One-time (1)'
            END as segment,
            COUNT(*) as customers
        FROM (
            SELECT customer_id, COUNT(*) as purchase_count
            FROM purchases
            GROUP BY customer_id
        ) t
        GROUP BY segment
        ORDER BY MIN(purchase_count) DESC
    """)
    print("\nCustomer Segments:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} customers")

    # Top products
    cur.execute("""
        SELECT p.name, COUNT(*) as purchases
        FROM purchases pu
        JOIN products p ON pu.product_id = p.product_id
        GROUP BY p.name
        ORDER BY purchases DESC
        LIMIT 5
    """)
    print("\nTop 5 Products:")
    for i, row in enumerate(cur.fetchall(), 1):
        print(f"  {i}. {row[0]}: {row[1]} purchases")

    print("\n" + "="*50)

def main():
    """Main execution function"""
    print("E-Commerce Sample Data Generator")
    print("="*50)

    try:
        # Connect to database
        conn = connect_db()
        print("✓ Connected to database")

        # Generate data
        products = generate_products(conn, num_products=100)
        customers = generate_customers(conn, num_customers=500)
        generate_purchases(conn, customers, products)

        # Refresh computed features
        refresh_features(conn)

        # Print statistics
        print_statistics(conn)

        print("\n✓ Sample data generation complete!")
        print("\nYou can now:")
        print("  1. Start the ML service: cd ml-service && uvicorn app.main:app --reload")
        print("  2. Test recommendations: curl http://localhost:8000/recommendations/1")

        conn.close()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise

if __name__ == "__main__":
    main()
