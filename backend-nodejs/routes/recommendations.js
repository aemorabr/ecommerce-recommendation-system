const express = require('express');
const router = express.Router();
const axios = require('axios');

const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:8000';

// Get recommendations (direct proxy to ML service)
router.get('/:customerId', async (req, res) => {
    try {
        const { customerId } = req.params;
        const { limit = 5 } = req.query;

        const response = await axios.get(
            `${ML_SERVICE_URL}/recommendations/${customerId}?limit=${limit}`
        );

        res.json(response.data);
    } catch (error) {
        console.error('Recommendation error:', error);

        if (error.response) {
            return res.status(error.response.status).json(error.response.data);
        }

        res.status(500).json({ error: 'Recommendation service unavailable' });
    }
});

// Get similar customers
router.get('/:customerId/similar', async (req, res) => {
    try {
        const { customerId } = req.params;
        const { limit = 5 } = req.query;

        const response = await axios.get(
            `${ML_SERVICE_URL}/similar-customers/${customerId}?limit=${limit}`
        );

        res.json(response.data);
    } catch (error) {
        console.error('Similar customers error:', error);

        if (error.response) {
            return res.status(error.response.status).json(error.response.data);
        }

        res.status(500).json({ error: 'Recommendation service unavailable' });
    }
});

module.exports = router;
