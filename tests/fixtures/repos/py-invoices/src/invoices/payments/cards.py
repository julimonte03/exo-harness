"""Card number checks. The sandbox only accepts published test cards."""

from __future__ import annotations

from ..core.errors import ValidationError

# Numbers published by the card networks for testing; no real card works in the sandbox.
TEST_CARDS = frozenset({"4111111111111111", "4242424242424242", "5555555555554444"})


def digits_of(number: str) -> str:
    digits = number.replace(" ", "").replace("-", "")
    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        raise ValidationError("a card number has 13 to 19 digits")
    return digits


def luhn_ok(number: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits_of(number))):
        digit = int(char) * (2 if index % 2 else 1)
        total += digit - 9 if digit > 9 else digit
    return total % 10 == 0


def validate_card(number: str, *, sandbox: bool) -> str:
    """Digits of a card the gateway may charge, or raise."""
    digits = digits_of(number)
    if not luhn_ok(digits):
        raise ValidationError("the card number fails the Luhn check")
    if sandbox and digits not in TEST_CARDS:
        raise ValidationError("the sandbox only accepts published test cards")
    return digits


def mask(number: str) -> str:
    digits = digits_of(number)
    return "*" * (len(digits) - 4) + digits[-4:]
