"""Core views for the bank application."""

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render

from apps.accounts.models import Account
from apps.transactions.models import Transaction


@login_required
def dashboard(request):
    """Show the main dashboard."""
    user = request.user

    # Get accounts
    accounts = Account.objects.filter(
        customer=user,
        status__in=["ACTIVE", "BLOCKED"],
    ).order_by("-created_at")

    # Calculate total balance
    total_balance = accounts.aggregate(
        total=Coalesce(Sum("balance"), 0)
    )["total"]

    # Get recent transactions
    account_ids = accounts.values_list("id", flat=True)
    recent_transactions = Transaction.objects.filter(
        source_account_id__in=account_ids
    ) | Transaction.objects.filter(
        destination_account_id__in=account_ids
    )
    recent_transactions = recent_transactions.distinct().order_by("-created_at")[:10]

    return render(
        request,
        "dashboard.html",
        {
            "user": user,
            "accounts": accounts,
            "total_balance": total_balance,
            "recent_transactions": recent_transactions,
        },
    )