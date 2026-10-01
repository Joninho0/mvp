"""Forms for accounts app."""

from decimal import Decimal

from django import forms

from .models import Account


class AccountForm(forms.ModelForm):
    """Form for creating accounts."""

    class Meta:
        model = Account
        fields = [
            "account_type",
            "daily_limit",
            "transaction_limit",
        ]
        widgets = {
            "account_type": forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
            "daily_limit": forms.NumberInput(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
            "transaction_limit": forms.NumberInput(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["daily_limit"].initial = Decimal("10000.00")
        self.fields["transaction_limit"].initial = Decimal("5000.00")