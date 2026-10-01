"""Forms for transactions app."""

from decimal import Decimal

from django import forms
from django.db import transaction as db_transaction

from apps.accounts.models import Account
from apps.ledger.models import EntryType, LedgerEntry
from apps.transactions.models import Transaction, TransactionStatus, TransactionType


class TransferForm(forms.Form):
    """Form for money transfers."""

    source_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        widget=forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
    )
    destination_account = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg", "placeholder": "Número da conta"}),
    )
    amount = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=18,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
    )
    reference = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["source_account"].queryset = Account.objects.filter(
            customer=self.user,
            status="ACTIVE",
        )

    def clean_amount(self):
        """Validate amount."""
        amount = self.cleaned_data["amount"]
        source_account = self.cleaned_data.get("source_account")

        if source_account and amount > source_account.transaction_limit:
            raise forms.ValidationError(
                f"Valor excede o limite por transação de {source_account.transaction_limit}"
            )

        if amount > source_account._get_remaining_daily_limit():
            raise forms.ValidationError(
                f"Valor excede o limite diário disponível ({source_account._get_remaining_daily_limit()})"
            )

        return amount

    def clean_destination_account(self):
        """Validate and find destination account."""
        account_number = self.cleaned_data["destination_account"]

        try:
            dest_account = Account.objects.get(
                account_number=account_number,
                status="ACTIVE",
            )
        except Account.DoesNotExist:
            raise forms.ValidationError("Conta de destino não encontrada ou inativa.")

        # Can't transfer to same account
        source_account = self.cleaned_data.get("source_account")
        if source_account and dest_account.id == source_account.id:
            raise forms.ValidationError("Não é possível transferir para a mesma conta.")

        return dest_account

    def save(self):
        """Execute the transfer."""
        source_account = self.cleaned_data["source_account"]
        dest_account = self.cleaned_data["destination_account"]
        amount = self.cleaned_data["amount"]
        reference = self.cleaned_data.get("reference", "")

        # Create transaction
        with db_transaction.atomic():
            tx = Transaction.objects.create(
                transaction_type=TransactionType.TRANSFER,
                status=TransactionStatus.PROCESSING,
                amount=amount,
                source_account=source_account,
                destination_account=dest_account,
                reference=reference,
            )

            # Create ledger entries
            LedgerEntry.create_transfer_entries(
                transaction_id=tx.id,
                source_account=source_account,
                destination_account=dest_account,
                amount=amount,
                description=f"Transferência para {dest_account.account_number}" if reference else None,
            )

            # Update daily limits
            source_account.daily_used += amount
            source_account.save(update_fields=["daily_used"])

            # Complete transaction
            tx.mark_completed()

        return tx


class DepositForm(forms.Form):
    """Form for deposits."""

    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        widget=forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
    )
    amount = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=18,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
    )
    reference = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["account"].queryset = Account.objects.filter(
            customer=self.user,
            status="ACTIVE",
        )

    def clean_amount(self):
        """Validate amount."""
        amount = self.cleaned_data["amount"]
        account = self.cleaned_data.get("account")

        if account and amount > account.transaction_limit:
            raise forms.ValidationError(
                f"Valor excede o limite por transação de {account.transaction_limit}"
            )

        return amount

    def save(self):
        """Execute the deposit."""
        account = self.cleaned_data["account"]
        amount = self.cleaned_data["amount"]
        reference = self.cleaned_data.get("reference", "")

        with db_transaction.atomic():
            # Create transaction
            tx = Transaction.objects.create(
                transaction_type=TransactionType.DEPOSIT,
                status=TransactionStatus.PROCESSING,
                amount=amount,
                destination_account=account,
                reference=reference or "Depósito",
            )

            # Create ledger entry
            balance_before = account.balance
            LedgerEntry.create_entry(
                transaction_id=tx.id,
                account=account,
                entry_type=EntryType.CREDIT,
                amount=amount,
                balance_before=balance_before,
                description=reference or "Depósito",
            )

            # Update balance
            account.balance += amount
            account.save(update_fields=["balance"])

            # Complete
            tx.mark_completed()

        return tx


class WithdrawalForm(forms.Form):
    """Form for withdrawals."""

    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        widget=forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
    )
    amount = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=18,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
    )
    reference = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg"}),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["account"].queryset = Account.objects.filter(
            customer=self.user,
            status="ACTIVE",
        )

    def clean_amount(self):
        """Validate amount."""
        amount = self.cleaned_data["amount"]
        account = self.cleaned_data.get("account")

        if account:
            if amount > account.balance:
                raise forms.ValidationError(
                    f"Saldo insuficiente. Disponível: {account.balance}"
                )

            if amount > account.transaction_limit:
                raise forms.ValidationError(
                    f"Valor excede o limite por transação de {account.transaction_limit}"
                )

            if amount > account._get_remaining_daily_limit():
                raise forms.ValidationError(
                    f"Valor excede o limite diário disponível ({account._get_remaining_daily_limit()})"
                )

        return amount

    def save(self):
        """Execute the withdrawal."""
        account = self.cleaned_data["account"]
        amount = self.cleaned_data["amount"]
        reference = self.cleaned_data.get("reference", "")

        with db_transaction.atomic():
            # Create transaction
            tx = Transaction.objects.create(
                transaction_type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.PROCESSING,
                amount=amount,
                source_account=account,
                reference=reference or "Saque",
            )

            # Create ledger entry
            balance_before = account.balance
            LedgerEntry.create_entry(
                transaction_id=tx.id,
                account=account,
                entry_type=EntryType.DEBIT,
                amount=amount,
                balance_before=balance_before,
                description=reference or "Saque",
            )

            # Update balance
            account.balance -= amount
            account.save(update_fields=["balance"])

            # Update daily limit
            account.daily_used += amount
            account.save(update_fields=["daily_used"])

            # Complete
            tx.mark_completed()

        return tx