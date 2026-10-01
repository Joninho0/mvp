"""Tests for money utilities."""

from decimal import Decimal

import pytest

from core.money import Money, Currency, parse_money


class TestMoney:
    """Tests for Money class."""

    def test_money_creation(self):
        """Test creating Money instances."""
        m1 = Money(100.00, "BRL")
        m2 = Money(Decimal("100.00"), "BRL")
        m3 = Money("100.00", "BRL")

        assert m1.amount == Decimal("100.00")
        assert m2.amount == Decimal("100.00")
        assert m3.amount == Decimal("100.00")

    def test_money_addition(self):
        """Test adding Money instances."""
        m1 = Money(100.00, "BRL")
        m2 = Money(50.00, "BRL")

        result = m1 + m2

        assert result.amount == Decimal("150.00")

    def test_money_subtraction(self):
        """Test subtracting Money instances."""
        m1 = Money(100.00, "BRL")
        m2 = Money(30.00, "BRL")

        result = m1 - m2

        assert result.amount == Decimal("70.00")

    def test_money_subtraction_prevents_negative(self):
        """Test that subtraction raises error for negative result."""
        m1 = Money(50.00, "BRL")
        m2 = Money(100.00, "BRL")

        with pytest.raises(ValueError):
            m1 - m2

    def test_money_multiplication(self):
        """Test multiplying Money by a factor."""
        m = Money(100.00, "BRL")
        result = m * 2

        assert result.amount == Decimal("200.00")

    def test_money_from_cents(self):
        """Test creating Money from cents."""
        m = Money.from_cents(10000, "BRL")  # 100.00

        assert m.amount == Decimal("100.00")

    def test_money_comparison(self):
        """Test comparing Money instances."""
        m1 = Money(100.00, "BRL")
        m2 = Money(50.00, "BRL")
        m3 = Money(100.00, "BRL")

        assert m1 > m2
        assert m2 < m1
        assert m1 == m3

    def test_zero_money(self):
        """Test creating zero Money."""
        m = Money.zero("BRL")

        assert m.is_zero() is True
        assert m.amount == Decimal("0")

    def test_money_cents(self):
        """Test converting to cents."""
        m = Money(100.00, "BRL")

        assert m.cents == 10000

    def test_money_formatting(self):
        """Test Money string formatting."""
        m = Money(1000.00, Currency("BRL", symbol="R$"))

        # Should format as R$ 1,000.00
        assert "R$" in str(m)
        assert "1,000" in str(m)


class TestCurrency:
    """Tests for Currency class."""

    def test_currency_creation(self):
        """Test creating Currency instances."""
        usd = Currency("USD", 2, "$")
        brl = Currency("BRL", 2, "R$")

        assert usd.code == "USD"
        assert usd.symbol == "$"
        assert brl.code == "BRL"

    def test_currency_multiplier(self):
        """Test currency multiplier (10^decimal_places)."""
        currency = Currency("BRL", decimal_places=2)

        assert currency.multiplier == Decimal("100")


class TestParseMoney:
    """Tests for parse_money function."""

    def test_parse_with_currency_symbol(self):
        """Test parsing money with currency symbol."""
        m = parse_money("R$ 100,00", "BRL")

        assert m.amount == Decimal("100.00")

    def test_parse_european_format(self):
        """Test parsing European number format."""
        m = parse_money("1.000,50", "BRL")

        assert m.amount == Decimal("1000.50")

    def test_parse_us_format(self):
        """Test parsing US number format."""
        m = parse_money("1,000.50", "BRL")

        assert m.amount == Decimal("1000.50")