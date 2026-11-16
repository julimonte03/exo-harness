import { useEffect, useState } from 'react';
import type { Product } from '@shop/shared';
import { fetchProducts } from '../api/client';

export type ProductsState = { products: Product[] | null; error: string | null };

export function useProducts(): ProductsState {
  const [state, setState] = useState<ProductsState>({ products: null, error: null });

  useEffect(() => {
    const controller = new AbortController();
    fetchProducts(controller.signal).then(
      (products) => setState({ products, error: null }),
      (err: Error) => err.name !== 'AbortError' && setState({ products: null, error: err.message }),
    );
    return () => controller.abort();
  }, []);

  return state;
}
