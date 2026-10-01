"""Views for transactions app."""

import uuid

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import DepositForm, TransferForm, WithdrawalForm
from .models import Transaction, TransactionStatus


@login_required
@require_http_methods(["GET"])
def transaction_list(request):
    """List all transactions for the current user."""
    from apps.accounts.models import Account

    # Get user's accounts
    account_ids = Account.objects.filter(
        customer=request.user
    ).values_list("id", flat=True)

    # Build query
    query = Q(source_account_id__in=account_ids) | Q(destination_account_id__in=account_ids)

    # Apply filters
    tx_type = request.GET.get("type")
    status = request.GET.get("status")
    date = request.GET.get("date")

    if tx_type:
        query &= Q(transaction_type=tx_type)
    if status:
        query &= Q(status=status)
    if date:
        query &= Q(created_at__date=date)

    # Get transactions
    transactions = (
        Transaction.objects.filter(query)
        .select_related("source_account", "destination_account")
        .order_by("-created_at")
    )

    # Paginate
    page = int(request.GET.get("page", 1))
    per_page = 25
    total = transactions.count()
    transactions = transactions[(page - 1) * per_page : page * per_page]
    has_next = total > page * per_page

    return render(
        request,
        "transactions/transaction_list.html",
        {
            "transactions": transactions,
            "page": page,
            "has_next": has_next,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def transfer_view(request):
    """Handle money transfers between accounts."""
    from apps.accounts.models import Account

    accounts = Account.objects.filter(
        customer=request.user,
        status="ACTIVE",
    ).order_by("-created_at")

    selected_account = request.GET.get("account")

    if request.method == "POST":
        form = TransferForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                transaction = form.save()
                return redirect("transactions:list")
            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = TransferForm(user=request.user)

    return render(
        request,
        "transactions/transfer_form.html",
        {
            "form": form,
            "accounts": accounts,
            "selected_account": selected_account,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def deposit_view(request):
    """Handle deposits to account."""
    from apps.accounts.models import Account

    accounts = Account.objects.filter(
        customer=request.user,
        status="ACTIVE",
    ).order_by("-created_at")

    selected_account = request.GET.get("account")

    if request.method == "POST":
        form = DepositForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                transaction = form.save()
                return redirect("accounts:detail", account_id=transaction.destination_account_id)
            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = DepositForm(user=request.user)

    return render(
        request,
        "transactions/deposit_form.html",
        {
            "form": form,
            "accounts": accounts,
            "selected_account": selected_account,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def withdraw_view(request):
    """Handle withdrawals from account."""
    from apps.accounts.models import Account

    accounts = Account.objects.filter(
        customer=request.user,
        status="ACTIVE",
    ).order_by("-created_at")

    selected_account = request.GET.get("account")
    available_balance = "0.00"

    if selected_account:
        try:
            account = get_object_or_404(Account, id=selected_account, customer=request.user)
            available_balance = account.balance
        except Http404:
            pass

    if request.method == "POST":
        form = WithdrawalForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                transaction = form.save()
                return redirect("accounts:detail", account_id=transaction.source_account_id)
            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = WithdrawalForm(user=request.user)

    return render(
        request,
        "transactions/withdraw_form.html",
        {
            "form": form,
            "accounts": accounts,
            "selected_account": selected_account,
            "available_balance": available_balance,
        },
    )