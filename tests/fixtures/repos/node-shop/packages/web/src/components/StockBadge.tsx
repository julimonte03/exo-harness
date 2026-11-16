import { colors } from '@shop/design-tokens';
import { LOW_STOCK_THRESHOLD } from '@shop/shared';

export type StockLevel = 'in-stock' | 'low-stock' | 'out-of-stock';

export function stockLevelFor(available: number): StockLevel {
  if (available <= 0) return 'out-of-stock';
  return available <= LOW_STOCK_THRESHOLD ? 'low-stock' : 'in-stock';
}

const BADGES: Record<StockLevel, { tone: string; label: (available: number) => string }> = {
  'in-stock': { tone: colors.success, label: () => 'In stock' },
  'low-stock': { tone: colors.warning, label: (available) => `Only ${available} left` },
  'out-of-stock': { tone: colors.danger, label: () => 'Sold out' },
};

export function StockBadge({ available }: { available: number }) {
  const level = stockLevelFor(available);
  const { tone, label } = BADGES[level];
  return (
    <span className={`badge badge--${level}`} style={{ color: tone }}>
      {label(available)}
    </span>
  );
}
