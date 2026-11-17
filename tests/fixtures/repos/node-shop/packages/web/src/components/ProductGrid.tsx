import { useMemo, useState } from 'react';
import type { Product } from '@shop/shared';
import type { ProductsState } from '@/hooks/useProducts';
import { ProductCard } from './ProductCard';

type SortKey = 'name' | 'price-asc' | 'price-desc';

const SORTERS: Record<SortKey, (a: Product, b: Product) => number> = {
  name: (a, b) => a.name.localeCompare(b.name),
  'price-asc': (a, b) => a.priceCents - b.priceCents,
  'price-desc': (a, b) => b.priceCents - a.priceCents,
};

interface ProductGridProps {
  state: ProductsState;
  onAdd: (product: Product, quantity: number) => void;
}

export function ProductGrid({ state, onAdd }: ProductGridProps) {
  const [sort, setSort] = useState<SortKey>('name');
  const [hideSoldOut, setHideSoldOut] = useState(false);

  const visible = useMemo(
    () => (state.products ?? []).filter((p) => !hideSoldOut || p.available > 0).sort(SORTERS[sort]),
    [state.products, sort, hideSoldOut],
  );

  if (state.error) return <p role="alert">Could not load products: {state.error}</p>;
  if (!state.products) return <p>Loading products...</p>;

  return (
    <div className="product-grid">
      <div className="product-grid__toolbar">
        <label>
          Sort by
          <select value={sort} onChange={(event) => setSort(event.target.value as SortKey)}>
            <option value="name">Name</option>
            <option value="price-asc">Price: low to high</option>
            <option value="price-desc">Price: high to low</option>
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={hideSoldOut}
            onChange={(event) => setHideSoldOut(event.target.checked)}
          />
          Hide sold out
        </label>
      </div>
      {visible.length === 0 ? (
        <p>No products match.</p>
      ) : (
        <div className="product-grid__items">
          {visible.map((product) => (
            <ProductCard key={product.id} product={product} onAdd={onAdd} />
          ))}
        </div>
      )}
    </div>
  );
}
