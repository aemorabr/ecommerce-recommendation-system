const express = require('express');
const router = express.Router();
const db = require('../services/database');

// Get customer by ID
router.get('/:id', async (req, res) => {
    try {
        const { id } = req.params;

        const result = await db.query(
            'SELECT * FROM customers WHERE customer_id = $1',
            [id]
        );

        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Customer not found' });
        }

        res.json(result.rows[0]);
    } catch (error) {
        console.error('Error fetching customer:', error);
        res.status(500).json({ error: 'Failed to fetch customer' });
    }
});

// Get customer purchase history
router.get('/:id/history', async (req, res) => {
    try {
        const { id } = req.params;
        const { limit = 20, offset = 0 } = req.query;

        const result = await db.query(`
            SELECT 
                p.*,
                pr.name as product_name,
                pr.category,
                pr.price as unit_price
            FROM purchases p
            JOIN products pr ON p.product_id = pr.product_id
            WHERE p.customer_id = $1
            ORDER BY p.purchase_date DESC
            LIMIT $2 OFFSET $3
        `, [id, limit, offset]);

        res.json({
            purchases: result.rows,
            total: result.rows.length
        });
    } catch (error) {
        console.error('Error fetching purchase history:', error);
        res.status(500).json({ error: 'Failed to fetch purchase history' });
    }
});

// Get customer analytics
router.get('/:id/analytics', async (req, res) => {
    try {
        const { id } = req.params;

        const result = await db.query(`
            SELECT * FROM customer_analytics
            WHERE customer_id = $1
        `, [id]);

        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Customer not found' });
        }

        res.json(result.rows[0]);
    } catch (error) {
        console.error('Error fetching customer analytics:', error);
        res.status(500).json({ error: 'Failed to fetch analytics' });
    }
});

module.exports = router;
