interface CategoryFilterProps {
  categories: string[];
  selected: string;
  onChange: (category: string) => void;
}

export default function CategoryFilter({ categories, selected, onChange }: CategoryFilterProps) {
  return (
    <div className="flex gap-2 flex-wrap">
      <button
        onClick={() => onChange('all')}
        className={`px-4 py-2 rounded-lg font-medium transition-colors ${
          selected === 'all'
            ? 'bg-primary-600 text-white'
            : 'bg-white text-gray-700 hover:bg-gray-100'
        }`}
      >
        All
      </button>

      {categories.map((category) => (
        <button
          key={category}
          onClick={() => onChange(category)}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            selected === category
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          {category}
        </button>
      ))}
    </div>
  );
}