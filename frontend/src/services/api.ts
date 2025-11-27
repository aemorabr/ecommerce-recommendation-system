import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Products
export const getProducts = async (category = null, limit = 50, offset = 0) => {
  const params = { limit, offset };
  if (category) params.category = category;

  const response = await api.get('/products', { params });
  return response.data;
};

export const getProduct = async (id) => {
  const response = await api.get(`/products/${id}`);
  return response.data;
};

export const getCategories = async () => {
  const response = await api.get('/products/meta/categories');
  return response.data;
};

// Recommendations
export const getRecommendations = async (customerId, limit = 5) => {
  const response = await api.get(`/products/recommendations/${customerId}`, {
    params: { limit }
  });
  return response.data;
};

// Customers
export const getCustomer = async (id) => {
  const response = await api.get(`/customers/${id}`);
  return response.data;
};

export const getCustomerHistory = async (id, limit = 20, offset = 0) => {
  const response = await api.get(`/customers/${id}/history`, {
    params: { limit, offset }
  });
  return response.data;
};

export const getCustomerAnalytics = async (id) => {
  const response = await api.get(`/customers/${id}/analytics`);
  return response.data;
};

export default api;
