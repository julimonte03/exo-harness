import { useState, type FormEvent } from 'react';
import { validateCheckout, type CheckoutErrors, type CheckoutValues } from './checkoutValidation';

const EMPTY: CheckoutValues = { email: '', fullName: '', postalCode: '', cardNumber: '', expiry: '' };

const FIELDS: { name: keyof CheckoutValues; label: string; autoComplete: string }[] = [
  { name: 'email', label: 'Email', autoComplete: 'email' },
  { name: 'fullName', label: 'Name on card', autoComplete: 'cc-name' },
  { name: 'postalCode', label: 'ZIP code', autoComplete: 'postal-code' },
  { name: 'cardNumber', label: 'Card number', autoComplete: 'cc-number' },
  { name: 'expiry', label: 'Expiry (MM/YY)', autoComplete: 'cc-exp' },
];

interface CheckoutFormProps {
  onSubmit: (values: CheckoutValues) => Promise<void>;
}

export function CheckoutForm({ onSubmit }: CheckoutFormProps) {
  const [values, setValues] = useState<CheckoutValues>(EMPTY);
  const [errors, setErrors] = useState<CheckoutErrors>({});
  const [submitting, setSubmitting] = useState(false);

  function update(name: keyof CheckoutValues, value: string) {
    setValues((current) => ({ ...current, [name]: value }));
    if (errors[name]) setErrors((current) => ({ ...current, [name]: undefined }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = validateCheckout(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setSubmitting(true);
    try {
      await onSubmit(values);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="checkout-form" onSubmit={handleSubmit} noValidate>
      {FIELDS.map(({ name, label, autoComplete }) => (
        <div key={name} className="checkout-form__field">
          <label htmlFor={`checkout-${name}`}>{label}</label>
          <input
            id={`checkout-${name}`}
            name={name}
            autoComplete={autoComplete}
            inputMode={name === 'cardNumber' || name === 'postalCode' ? 'numeric' : undefined}
            value={values[name]}
            aria-invalid={Boolean(errors[name])}
            aria-describedby={errors[name] ? `checkout-${name}-error` : undefined}
            onChange={(event) => update(name, event.target.value)}
          />
          {errors[name] && (
            <p id={`checkout-${name}-error`} className="checkout-form__error">
              {errors[name]}
            </p>
          )}
        </div>
      ))}
      <button type="submit" disabled={submitting}>
        {submitting ? 'Placing order...' : 'Place order'}
      </button>
    </form>
  );
}
