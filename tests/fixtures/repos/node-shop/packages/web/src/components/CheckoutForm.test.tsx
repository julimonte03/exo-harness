import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { CheckoutForm } from './CheckoutForm';
import { isExpired, passesLuhn, validateCheckout } from './checkoutValidation';

const today = new Date(2026, 10, 16);
const card = '4111 1111 1111 1111';

it('accepts the published Visa test card and rejects a typo', () => {
  expect(passesLuhn(card)).toBe(true);
  expect(passesLuhn('4111 1111 1111 1112')).toBe(false);
});

it('keeps a card valid through its expiry month', () => {
  expect(isExpired('11/26', today)).toBe(false);
  expect(isExpired('10/26', today)).toBe(true);
});

it('returns no errors for a complete form', () => {
  const values = { email: 'buyer@example.com', fullName: 'Test Buyer', postalCode: '94105' };
  expect(validateCheckout({ ...values, cardNumber: card, expiry: '12/30' }, today)).toEqual({});
});

it('does not submit while fields are invalid', () => {
  const onSubmit = vi.fn();
  render(<CheckoutForm onSubmit={onSubmit} />);
  fireEvent.click(screen.getByRole('button', { name: 'Place order' }));
  expect(screen.getByText('Enter a valid email address')).toBeTruthy();
  expect(onSubmit).not.toHaveBeenCalled();
});
