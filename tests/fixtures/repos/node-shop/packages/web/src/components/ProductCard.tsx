import { useState } from 'react';
import { MAX_QTY_PER_LINE, type Product } from '@shop/shared';
import { Price } from './Price';
import { StockBadge } from './StockBadge';

interface ProductCardProps {
  product: Product;
  onAdd: (product: Product, quantity: number) => void;
}

export function ProductCard({ product, onAdd }: ProductCardProps) {
  const [quantity, setQuantity] = useState(1);
  const maxQuantity = Math.min(product.available, MAX_QTY_PER_LINE);
  const soldOut = maxQuantity <= 0;
  const options = Array.from({ length: Math.max(maxQuantity, 1) }, (_, i) => i + 1);

  return (
    <article className="product-card" aria-labelledby={`product-${product.id}`}>
      <div className="product-card__image" aria-hidden="true">
        {product.name.slice(0, 1)}
      </div>
      <h2 id={`product-${product.id}`}>{product.name}</h2>
      <Price cents={product.priceCents} />
      <StockBadge available={product.available} />
      <label>
        Quantity
        <select
          value={quantity}
          disabled={soldOut}
          onChange={(event) => setQuantity(Number(event.target.value))}
        >
          {options.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </label>
      <button type="button" disabled={soldOut} onClick={() => onAdd(product, quantity)}>
        {soldOut ? 'Sold out' : 'Add to cart'}
      </button>
    </article>
  );
}
