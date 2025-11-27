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
export const getProducts = async (category: string | null = null, limit: number = 50, offset: number = 0): Promise<any> => {
  const params: any = { limit, offset };
  if (category) params.category = category;

  const response = await api.get('/products', { params });
  return response.data;
};

export const getProduct = async (id: number): Promise<any> => {
  const response = await api.get(`/products/${id}`);
  return response.data;
};

export const getCategories = async (): Promise<any> => {
  const response = await api.get('/products/meta/categories');
  return response.data;
};

// Recommendations
export const getRecommendations = async (customerId: number, limit: number = 5): Promise<any> => {
  const response = await api.get(`/products/recommendations/${customerId}`, {
    params: { limit }
  });
  return response.data;
};

// Customers
export const getCustomer = async (id: number): Promise<any> => {
  const response = await api.get(`/customers/${id}`);
  return response.data;
};

export const getCustomerHistory = async (id: number, limit: number = 20, offset: number = 0): Promise<any> => {
  const response = await api.get(`/customers/${id}/history`, {
    params: { limit, offset }
  });
  return response.data;
};

export const getCustomerAnalytics = async (id: number): Promise<any> => {
  const response = await api.get(`/customers/${id}/analytics`);
  return response.data;
};

// Search
export const searchProducts = async (query: string, limit: number = 20): Promise<any> => {
  const response = await api.get('/products/search', {
    params: { q: query, limit }
  });
  return response.data;
};

export default api;
