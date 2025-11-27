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
  const [customerId] = useState<number>(1); // Demo: hardcoded customer ID

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
              Powered by AI Recommendations
            </p>
          </div>
        </header>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Recommendations Section */}
          <section className="mb-12">
            <RecommendedProducts customerId={customerId} />
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
