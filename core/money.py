"""
Money utilities for the bank domain.

This module provides Money class and utilities for handling monetary values
with proper decimal precision and rounding.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from django.conf import settings


# Default currency configuration
DEFAULT_CURRENCY = "BRL"


@dataclass(frozen=True, slots=True)
class Currency:
    """Represents a currency with its configuration."""

    code: str
    decimal_places: int = 2
    symbol: str = ""

    def __post_init__(self):
        # Ensure code is uppercase
        object.__setattr__(self, "code", self.code.upper())

    @property
    def multiplier(self) -> Decimal:
        """Returns the multiplier for this currency (10^decimal_places)."""
        return Decimal(str(10**self.decimal_places))


class Money:
    """
    Represents a monetary value with proper decimal handling.

    IMPORTANT: Money never uses float. Always use Decimal for financial
    calculations to avoid floating-point precision errors.

    All arithmetic operations use ROUND_HALF_EVEN (banker's rounding)
    to avoid bias in repeated calculations.
    """

    __slots__ = ("_amount", "_currency")

    def __init__(
        self,
        amount: Decimal | int | str | float,
        currency: str | Currency = DEFAULT_CURRENCY,
    ) -> None:
        """
        Initialize Money with an amount and currency.

        Args:
            amount: The monetary value (Decimal, int, str, or float)
            currency: Currency code or Currency instance

        Raises:
            ValueError: If amount is negative (for positive-only operations)
            InvalidOperation: If amount cannot be parsed as Decimal
        """
        if isinstance(currency, str):
            currency = Currency(currency)

        # Convert to Decimal safely
        if isinstance(amount, float):
            # Float is imprecise - warn and convert with context
            # In production, float should never be used for money
            decimal_amount = Decimal(str(amount))
        elif isinstance(amount, int):
            decimal_amount = Decimal(amount)
        else:
            decimal_amount = Decimal(str(amount))

        # Round to currency precision
        decimal_amount = decimal_amount.quantize(
            Decimal(f"1.{'0' * currency.decimal_places}"),
            rounding=ROUND_HALF_EVEN,
        )

        # Validate no negative values for basic operations
        if decimal_amount < Decimal("0"):
            raise ValueError("Money amount cannot be negative")

        object.__setattr__(self, "_amount", decimal_amount)
        object.__setattr__(self, "_currency", currency)

    @classmethod
    def zero(cls, currency: str | Currency = DEFAULT_CURREency) -> "Money":
        """Create Money with zero value."""
        return cls(Decimal("0"), currency)

    @classmethod
    def from_cents(cls, cents: int, currency: str | Currency = DEFAULT_CURRENCY) -> "Money":
        """
        Create Money from cents (integer) representation.

        Useful for storing values as integers in the database.
        """
        if isinstance(currency, str):
            currency = Currency(currency)

        decimal_amount = Decimal(cents) / currency.multiplier
        return cls(decimal_amount, currency)

    @property
    def amount(self) -> Decimal:
        """Returns the amount as Decimal."""
        return self._amount

    @property
    def currency(self) -> Currency:
        """Returns the currency."""
        return self._currency

    @property
    def code(self) -> str:
        """Returns the currency code."""
        return self._currency.code

    @property
    def cents(self) -> int:
        """Returns the amount in smallest currency unit (cents)."""
        return int(self._amount * self._currency.multiplier)

    def is_zero(self) -> bool:
        """Check if the amount is zero."""
        return self._amount == Decimal("0")

    def is_positive(self) -> bool:
        """Check if the amount is positive."""
        return self._amount > Decimal("0")

    def is_negative(self) -> bool:
        """Check if the amount is negative."""
        return self._amount < Decimal("0")

    def __repr__(self) -> str:
        return f"Money({self._amount} {self._code})"

    def __str__(self) -> str:
        """Format as currency string."""
        return f"{self._currency.symbol}{self._amount:,.{self._currency.decimal_places}f}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return False
        return self._amount == other._amount and self._currency == other._currency

    def __hash__(self) -> int:
        return hash((self._amount, self._currency.code))

    def __add__(self, other: "Money") -> "Money":
        if self._currency != other._currency:
            raise ValueError(f"Cannot add {other._currency.code} to {self._currency.code}")
        return Money(self._amount + other._amount, self._currency)

    def __sub__(self, other: "Money") -> "Money":
        if self._currency != other._currency:
            raise ValueError(f"Cannot subtract {other._currency.code} from {self._currency.code}")
        result = self._amount - other._amount
        if result < Decimal("0"):
            raise ValueError("Result cannot be negative")
        return Money(result, self._currency)

    def __mul__(self, multiplier: Decimal | int | float) -> "Money":
        if isinstance(multiplier, (int, float)):
            multiplier = Decimal(str(multiplier))
        result = (self._amount * multiplier).quantize(
            Decimal(f"1.{'0' * self._currency.decimal_places}"),
            rounding=ROUND_HALF_EVEN,
        )
        return Money(result, self._currency)

    def __truediv__(self, divisor: Decimal | int | float) -> Decimal:
        if isinstance(divisor, (int, float)):
            divisor = Decimal(str(divisor))
        if divisor == Decimal("0"):
            raise ValueError("Division by zero")
        return self._amount / divisor

    def __lt__(self, other: "Money") -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self._currency != other._currency:
            raise ValueError(f"Cannot compare {other._currency.code} to {self._currency.code}")
        return self._amount < other._amount

    def __le__(self, other: "Money") -> bool:
        return self == other or self < other

    def __gt__(self, other: "Money") -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self._currency != other._currency:
            raise ValueError(f"Cannot compare {other._currency.code} to {self._currency.code}")
        return self._amount > other._amount

    def __ge__(self, other: "Money") -> bool:
        return self == other or self > other

    def __neg__(self) -> "Money":
        """Return the negated value."""
        return Money(-self._amount, self._currency)

    def abs(self) -> "Money":
        """Return the absolute value."""
        return Money(abs(self._amount), self._currency)

    def max(self, other: "Money") -> "Money":
        """Return the maximum of two Money values."""
        return self if self >= other else other

    def min(self, other: "Money") -> "Money":
        """Return the minimum of two Money values."""
        return self if self <= other else other

    def scale_to_decimal_places(self, decimal_places: int, rounding: str = ROUND_HALF_EVEN) -> "Money":
        """Scale to different decimal places."""
        if decimal_places < 0:
            raise ValueError("Decimal places cannot be negative")

        factor = Decimal(str(10**decimal_places))
        new_amount = (self._amount * factor).quantize(
            Decimal("1"),
            rounding=rounding,
        ) / Decimal(str(10**self._currency.decimal_places))

        new_currency = Currency(self._currency.code, decimal_places, self._currency.symbol)
        return Money(new_amount, new_currency)


def parse_money(value: str, currency: str | Currency = DEFAULT_CURRENCY) -> Money:
    """
    Parse a string value into Money.

    Handles common formats like:
    - "100.00"
    - "100,00"
    - "R$ 100,00"
    - "USD 100.00"

    Args:
        value: String representation of the amount
        currency: Currency code or instance

    Returns:
        Money instance

    Raises:
        ValueError: If the value cannot be parsed
    """
    # Remove currency symbols and whitespace
    cleaned = value.strip()

    # Remove common currency symbols
    symbols_to_remove = ["R$", "$", "€", "£", "¥"]
    for symbol in symbols_to_remove:
        cleaned = cleaned.replace(symbol, "").strip()

    # Handle different decimal separators
    if "," in cleaned and "." in cleaned:
        # Both present - assume European format
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        # Only comma - likely European format
        cleaned = cleaned.replace(",", ".")
    elif cleaned.count("-") > 1:
        raise ValueError(f"Invalid monetary value: {value}")

    try:
        return Money(Decimal(cleaned), currency)
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Cannot parse '{value}' as money: {e}")