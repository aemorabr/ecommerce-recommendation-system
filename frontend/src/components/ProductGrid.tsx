import Image from 'next/image';

export default function ProductGrid({ products }) {
  if (!products || products.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No products found</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {products.map((product) => (
        <div
          key={product.product_id}
          className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow duration-300"
        >
          <div className="relative h-48 bg-gray-200">
            <Image
              src={product.image_url || '/placeholder.png'}
              alt={product.name}
              fill
              className="object-cover"
            />
          </div>

          <div className="p-4">
            <span className="inline-block px-2 py-1 text-xs font-semibold text-primary-700 bg-primary-50 rounded-full mb-2">
              {product.category}
            </span>

            <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
              {product.name}
            </h3>

            <p className="text-sm text-gray-600 mb-4 line-clamp-2">
              {product.description}
            </p>

            <div className="flex justify-between items-center">
              <span className="text-2xl font-bold text-gray-900">
                ${parseFloat(product.price).toFixed(2)}
              </span>

              <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
                Add to Cart
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
