-- E-Commerce Recommendation System Database Schema
-- PostgreSQL 15+

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Drop existing tables if they exist
DROP TABLE IF EXISTS customer_embeddings CASCADE;
DROP TABLE IF EXISTS customer_features CASCADE;
DROP TABLE IF EXISTS purchases CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS products CASCADE;

-- Products table
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    description TEXT,
    image_url VARCHAR(500),
    stock_quantity INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index on category for faster filtering
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_price ON products(price);

-- Customers table
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_customers_email ON customers(email);

-- Purchase history
CREATE TABLE purchases (
    purchase_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    quantity INT NOT NULL CHECK (quantity > 0),
    purchase_date TIMESTAMP DEFAULT NOW(),
    total_amount DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0)
);

-- Indexes for performance
CREATE INDEX idx_purchases_customer ON purchases(customer_id);
CREATE INDEX idx_purchases_product ON purchases(product_id);
CREATE INDEX idx_purchases_date ON purchases(purchase_date);

-- Customer features table (computed via PL/pgSQL)
CREATE TABLE customer_features (
    customer_id INT PRIMARY KEY REFERENCES customers(customer_id) ON DELETE CASCADE,
    total_purchases INT DEFAULT 0,
    total_spent DECIMAL(10,2) DEFAULT 0,
    avg_order_value DECIMAL(10,2) DEFAULT 0,
    favorite_category VARCHAR(100),
    last_purchase_date TIMESTAMP,
    purchase_frequency DECIMAL(5,2), -- purchases per month
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Customer embeddings for similarity search
CREATE TABLE customer_embeddings (
    customer_id INT PRIMARY KEY REFERENCES customers(customer_id) ON DELETE CASCADE,
    embedding vector(128), -- Adjust dimension based on your model
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX idx_customer_embeddings_vector ON customer_embeddings 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Function to refresh customer features
CREATE OR REPLACE FUNCTION refresh_customer_features()
RETURNS void AS $$
BEGIN
    -- Truncate and rebuild features
    TRUNCATE customer_features;

    INSERT INTO customer_features (
        customer_id,
        total_purchases,
        total_spent,
        avg_order_value,
        favorite_category,
        last_purchase_date,
        purchase_frequency
    )
    SELECT 
        c.customer_id,
        COALESCE(COUNT(p.purchase_id), 0) as total_purchases,
        COALESCE(SUM(p.total_amount), 0) as total_spent,
        COALESCE(AVG(p.total_amount), 0) as avg_order_value,
        (
            SELECT pr.category
            FROM purchases p2
            JOIN products pr ON p2.product_id = pr.product_id
            WHERE p2.customer_id = c.customer_id
            GROUP BY pr.category
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ) as favorite_category,
        MAX(p.purchase_date) as last_purchase_date,
        CASE 
            WHEN MAX(p.purchase_date) IS NOT NULL AND MIN(p.purchase_date) IS NOT NULL THEN
                COUNT(p.purchase_id)::DECIMAL / 
                GREATEST(
                    EXTRACT(EPOCH FROM (MAX(p.purchase_date) - MIN(p.purchase_date))) / (30 * 24 * 3600),
                    1
                )
            ELSE 0
        END as purchase_frequency
    FROM customers c
    LEFT JOIN purchases p ON c.customer_id = p.customer_id
    GROUP BY c.customer_id;

    -- Update timestamp
    UPDATE customer_features SET updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to get customer purchase vector (for similarity)
CREATE OR REPLACE FUNCTION get_customer_purchase_vector(cust_id INT)
RETURNS TABLE(product_id INT, purchase_count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.product_id,
        COUNT(*)::BIGINT as purchase_count
    FROM purchases p
    WHERE p.customer_id = cust_id
    GROUP BY p.product_id
    ORDER BY p.product_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get popular products
CREATE OR REPLACE FUNCTION get_popular_products(limit_count INT DEFAULT 10)
RETURNS TABLE(
    product_id INT,
    product_name VARCHAR,
    category VARCHAR,
    purchase_count BIGINT,
    total_revenue DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pr.product_id,
        pr.name,
        pr.category,
        COUNT(p.purchase_id)::BIGINT as purchase_count,
        SUM(p.total_amount) as total_revenue
    FROM products pr
    LEFT JOIN purchases p ON pr.product_id = p.product_id
    GROUP BY pr.product_id, pr.name, pr.category
    ORDER BY purchase_count DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update customer features on new purchase
CREATE OR REPLACE FUNCTION update_customer_features_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- Update or insert customer features
    INSERT INTO customer_features (
        customer_id,
        total_purchases,
        total_spent,
        avg_order_value,
        last_purchase_date
    )
    SELECT 
        NEW.customer_id,
        COUNT(*),
        SUM(total_amount),
        AVG(total_amount),
        MAX(purchase_date)
    FROM purchases
    WHERE customer_id = NEW.customer_id
    GROUP BY customer_id
    ON CONFLICT (customer_id) 
    DO UPDATE SET
        total_purchases = EXCLUDED.total_purchases,
        total_spent = EXCLUDED.total_spent,
        avg_order_value = EXCLUDED.avg_order_value,
        last_purchase_date = EXCLUDED.last_purchase_date,
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_customer_features
AFTER INSERT ON purchases
FOR EACH ROW
EXECUTE FUNCTION update_customer_features_trigger();

-- Create views for analytics
CREATE OR REPLACE VIEW customer_analytics AS
SELECT 
    c.customer_id,
    c.name,
    c.email,
    cf.total_purchases,
    cf.total_spent,
    cf.avg_order_value,
    cf.favorite_category,
    cf.last_purchase_date,
    cf.purchase_frequency,
    CASE 
        WHEN cf.last_purchase_date > NOW() - INTERVAL '30 days' THEN 'Active'
        WHEN cf.last_purchase_date > NOW() - INTERVAL '90 days' THEN 'At Risk'
        ELSE 'Inactive'
    END as customer_status
FROM customers c
LEFT JOIN customer_features cf ON c.customer_id = cf.customer_id;

CREATE OR REPLACE VIEW product_analytics AS
SELECT 
    p.product_id,
    p.name,
    p.category,
    p.price,
    COUNT(pu.purchase_id) as times_purchased,
    SUM(pu.quantity) as total_quantity_sold,
    SUM(pu.total_amount) as total_revenue,
    AVG(pu.total_amount) as avg_transaction_value
FROM products p
LEFT JOIN purchases pu ON p.product_id = pu.product_id
GROUP BY p.product_id, p.name, p.category, p.price;

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO your_app_user;

-- Insert some initial categories for reference
COMMENT ON TABLE products IS 'Product catalog with categories: Electronics, Clothing, Books, Home & Garden, Sports';
COMMENT ON TABLE purchases IS 'Customer purchase history for recommendation engine';
COMMENT ON TABLE customer_features IS 'Computed features for ML model, updated via triggers and batch jobs';
COMMENT ON TABLE customer_embeddings IS 'Vector embeddings for customer similarity search using pgvector';
