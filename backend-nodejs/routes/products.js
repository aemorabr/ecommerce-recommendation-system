const express = require('express');
const router = express.Router();
const db = require('../services/database');
const axios = require('axios');

const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:8000';

// Get all products
router.get('/', async (req, res) => {
    try {
        const { category, limit = 50, offset = 0 } = req.query;

        let query = 'SELECT * FROM products';
        const params = [];

        if (category) {
            query += ' WHERE category = $1';
            params.push(category);
        }

        query += ' ORDER BY product_id LIMIT $' + (params.length + 1) + ' OFFSET $' + (params.length + 2);
        params.push(limit, offset);

        const result = await db.query(query, params);

        res.json({
            products: result.rows,
            total: result.rows.length,
            limit: parseInt(limit),
            offset: parseInt(offset)
        });
    } catch (error) {
        console.error('Error fetching products:', error);
        res.status(500).json({ error: 'Failed to fetch products' });
    }
});

// Get product by ID
router.get('/:id', async (req, res) => {
    try {
        const { id } = req.params;

        const result = await db.query(
            'SELECT * FROM products WHERE product_id = $1',
            [id]
        );

        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Product not found' });
        }

        res.json(result.rows[0]);
    } catch (error) {
        console.error('Error fetching product:', error);
        res.status(500).json({ error: 'Failed to fetch product' });
    }
});

// Get product recommendations for a customer
router.get('/recommendations/:customerId', async (req, res) => {
    try {
        const { customerId } = req.params;
        const limit = req.query.limit || 5;

        // Call ML service
        const mlResponse = await axios.get(
            `${ML_SERVICE_URL}/recommendations/${customerId}?limit=${limit}`
        );

        const recommendations = mlResponse.data;

        // Enrich with product details
        const productIds = recommendations.map(r => r.product_id);

        if (productIds.length === 0) {
            return res.json([]);
        }

        const productsResult = await db.query(
            'SELECT * FROM products WHERE product_id = ANY($1)',
            [productIds]
        );

        // Merge recommendations with product details
        const enriched = recommendations.map(rec => {
            const product = productsResult.rows.find(p => p.product_id === rec.product_id);
            return {
                ...product,
                recommendation_score: rec.score,
                recommendation_reason: rec.reason
            };
        });

        res.json(enriched);
    } catch (error) {
        console.error('Recommendation error:', error);

        if (error.response?.status === 404) {
            return res.status(404).json({ error: 'Customer not found' });
        }

        res.status(500).json({ error: 'Failed to get recommendations' });
    }
});

// Get product categories
router.get('/meta/categories', async (req, res) => {
    try {
        const result = await db.query(
            'SELECT DISTINCT category FROM products ORDER BY category'
        );

        res.json(result.rows.map(r => r.category));
    } catch (error) {
        console.error('Error fetching categories:', error);
        res.status(500).json({ error: 'Failed to fetch categories' });
    }
});

module.exports = router;
