import { useEffect, useState } from 'react';
import Image from 'next/image';
import { getRecommendations } from '@/services/api';

interface Product {
  product_id: number;
  name: string;
  description?: string;
  price: number | string;
  category?: string;
  image_url?: string;
  recommendation_reason?: string;
  score?: number;
}

interface RecommendedProductsProps {
  customerId: number;
  limit?: number;
}

export default function RecommendedProducts({ customerId, limit = 5 }: RecommendedProductsProps) {
  const [recommendations, setRecommendations] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRecommendations();
  }, [customerId, limit]);

  const loadRecommendations = async (): Promise<void> => {
    try {
      setLoading(true);
      const data = await getRecommendations(customerId, limit);
      setRecommendations(data || []);
    } catch (error) {
      console.error('Failed to load recommendations:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Recommended For You
        </h2>
        <div className="animate-pulse flex space-x-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex-1 h-48 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!recommendations || recommendations.length === 0) {
    return null;
  }

  const getReasonBadge = (reason?: string): JSX.Element => {
    if (reason === 'customers_like_you') {
      return (
        <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-green-700 bg-green-50 rounded-full">
          ✨ Customers like you bought this
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-700 bg-blue-50 rounded-full">
        🔥 Popular choice
      </span>
    );
  };

  return (
    <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        Recommended For You
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {recommendations.map((product) => (
          <div
            key={product.product_id}
            className="bg-white rounded-lg shadow overflow-hidden hover:shadow-lg transition-shadow"
          >
            <div className="relative h-40 bg-gray-200">
              <Image
                src={product.image_url || '/placeholder.png'}
                alt={product.name}
                fill
                className="object-cover"
              />
            </div>

            <div className="p-3">
              {getReasonBadge(product.recommendation_reason)}

              <h3 className="text-sm font-semibold text-gray-900 mt-2 mb-1 line-clamp-2">
                {product.name}
              </h3>

              <div className="flex justify-between items-center mt-2">
                <span className="text-lg font-bold text-gray-900">
                  ${parseFloat(product.price.toString()).toFixed(2)}
                </span>

                <button className="px-3 py-1 text-sm bg-primary-600 text-white rounded hover:bg-primary-700 transition-colors">
                  Add
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
