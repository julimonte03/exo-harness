export interface CheckoutValues {
  email: string;
  fullName: string;
  postalCode: string;
  cardNumber: string;
  /** MM/YY, as printed on the card. */
  expiry: string;
}

export type CheckoutErrors = Partial<Record<keyof CheckoutValues, string>>;

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const US_ZIP = /^\d{5}(-\d{4})?$/;
const EXPIRY = /^(0[1-9]|1[0-2])\/(\d{2})$/;

/** Luhn checksum: catches typos before the payment provider sees the number. */
export function passesLuhn(cardNumber: string): boolean {
  const digits = cardNumber.replace(/[\s-]/g, '');
  if (!/^\d{13,19}$/.test(digits)) return false;
  let sum = 0;
  for (let i = 0; i < digits.length; i += 1) {
    let digit = Number(digits[digits.length - 1 - i]);
    if (i % 2 === 1) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
  }
  return sum % 10 === 0;
}

/** A card stays valid through the last day of its expiry month. */
export function isExpired(expiry: string, today = new Date()): boolean {
  const match = EXPIRY.exec(expiry.trim());
  if (!match) return true;
  const month = Number(match[1]);
  const year = 2000 + Number(match[2]);
  const currentYear = today.getFullYear();
  return year < currentYear || (year === currentYear && month < today.getMonth() + 1);
}

export function validateCheckout(values: CheckoutValues, today = new Date()): CheckoutErrors {
  const errors: CheckoutErrors = {};
  if (!EMAIL.test(values.email.trim())) errors.email = 'Enter a valid email address';
  if (values.fullName.trim().length < 2) errors.fullName = 'Enter the name on the card';
  if (!US_ZIP.test(values.postalCode.trim())) errors.postalCode = 'Use a 5-digit ZIP code';
  if (!passesLuhn(values.cardNumber)) errors.cardNumber = 'Card number is not valid';
  if (isExpired(values.expiry, today)) errors.expiry = 'Card is expired or not in MM/YY format';
  return errors;
}
