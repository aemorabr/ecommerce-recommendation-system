import { useState, useEffect } from 'react';
import Head from 'next/head';
import ProductGrid from '@/components/ProductGrid';
import RecommendedProducts from '@/components/RecommendedProducts';
import CategoryFilter from '@/components/CategoryFilter';
import { getProducts, getCategories } from '@/services/api';

interface Product {
  product_id: number;
  name: string;
  description: string;
  price: number | string;
  category: string;
  image_url?: string;
}

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [loading, setLoading] = useState<boolean>(true);
  const [customerId, setCustomerId] = useState<number>(1);
  const [recommendationLimit, setRecommendationLimit] = useState<number>(5);
  const [strategy, setStrategy] = useState<string>('hybrid');

  useEffect(() => {
    loadData();
  }, [selectedCategory]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [productsData, categoriesData] = await Promise.all([
        getProducts(selectedCategory === 'all' ? null : selectedCategory),
        getCategories()
      ]);
      setProducts(productsData.products || []);
      setCategories(categoriesData || []);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>E-Commerce AI Recommendations</title>
        <meta name="description" content="AI-powered product recommendations" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <main className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <h1 className="text-3xl font-bold text-gray-900">
              E-Commerce Store
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              Powered by AI Recommendations-Allan Mora &lt;allanmb@me.com&gt;
            </p>
          </div>
        </header>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Test Form Section */}
          <section className="mb-8 bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Test Recommendations
            </h2>
            <div className="flex flex-wrap gap-4 items-end">
              <div className="flex-1 min-w-[200px]">
                <label htmlFor="customerId" className="block text-sm font-medium text-gray-700 mb-2">
                  Customer ID
                </label>
                <input
                  id="customerId"
                  type="number"
                  min="1"
                  max="500"
                  value={customerId}
                  onChange={(e) => setCustomerId(parseInt(e.target.value) || 1)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Enter customer ID (1-500)"
                />
              </div>
              <div className="flex-1 min-w-[200px]">
                <label htmlFor="strategy" className="block text-sm font-medium text-gray-700 mb-2">
                  Recommendation Strategy
                </label>
                <select
                  id="strategy"
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
                >
                  <option value="hybrid">🔀 Hybrid (CF + Content)</option>
                  <option value="cf">👥 Collaborative Filtering</option>
                  <option value="content">📝 Content-Based</option>
                  <option value="popular">🔥 Popular Products</option>
                </select>
              </div>
              <div className="flex-1 min-w-[200px]">
                <label htmlFor="limit" className="block text-sm font-medium text-gray-700 mb-2">
                  Number of Recommendations
                </label>
                <input
                  id="limit"
                  type="number"
                  min="1"
                  max="20"
                  value={recommendationLimit}
                  onChange={(e) => setRecommendationLimit(parseInt(e.target.value) || 5)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Enter limit (1-20)"
                />
              </div>
              <div className="flex-shrink-0">
                <p className="text-sm text-gray-500">
                  Customer: <span className="font-semibold text-gray-900">{customerId}</span> |
                  Strategy: <span className="font-semibold text-gray-900">{strategy}</span> |
                  Limit: <span className="font-semibold text-gray-900">{recommendationLimit}</span>
                </p>
              </div>
            </div>
          </section>

          {/* Recommendations Section */}
          <section className="mb-12">
            <RecommendedProducts customerId={customerId} limit={recommendationLimit} strategy={strategy} />
          </section>

          {/* Products Section */}
          <section>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-900">
                All Products
              </h2>
              <CategoryFilter
                categories={categories}
                selected={selectedCategory}
                onChange={setSelectedCategory}
              />
            </div>

            {loading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
                <p className="mt-4 text-gray-600">Loading products...</p>
              </div>
            ) : (
              <ProductGrid products={products} />
            )}
          </section>
        </div>
      </main>
    </>
  );
}