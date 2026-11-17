import { formatCents } from '@shop/shared';

interface PriceProps {
  cents: number;
  strike?: boolean;
}

export function Price({ cents, strike = false }: PriceProps) {
  const text = formatCents(cents);
  return strike ? <s className="price price--old">{text}</s> : <span className="price">{text}</span>;
}
