"""Views for accounts app."""

import uuid

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import AccountForm
from .models import Account


@login_required
@require_http_methods(["GET"])
def account_list(request):
    """List all accounts for the current user."""
    accounts = Account.objects.filter(
        customer=request.user,
        status__in=["ACTIVE", "BLOCKED"],
    ).order_by("-created_at")

    return render(
        request,
        "accounts/account_list.html",
        {"accounts": accounts},
    )


@login_required
@require_http_methods(["GET"])
def account_detail(request, account_id):
    """Show account details."""
    try:
        account = get_object_or_404(
            Account.objects.prefetch_related(
                Prefetch(
                    "ledger_entries",
                    queryset=Account.ledger_entries.all().order_by("-created_at")[:10],
                )
            ),
            id=account_id,
            customer=request.user,
        )
    except Http404:
        return render(
            request,
            "404.html",
            {"message": "Account not found"},
            status=404,
        )

    return render(
        request,
        "accounts/account_detail.html",
        {
            "account": account,
            "entries": account.ledger_entries.all()[:10],
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def account_create(request):
    """Create a new account."""
    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.customer = request.user
            account.account_number = Account.generate_account_number()
            account.save()
            return redirect("accounts:detail", account_id=account.id)
    else:
        form = AccountForm()
    return render(
        request,
        "accounts/account_form.html",
        {"form": form},
    )


@login_required
@require_http_methods(["GET"])
def account_statement(request, account_id):
    """Show account statement."""
    from django.db.models import Q
    from apps.ledger.models import EntryType, LedgerEntry

    try:
        account = get_object_or_404(Account, id=account_id, customer=request.user)
    except Http404:
        return render(
            request,
            "404.html",
            {"message": "Account not found"},
            status=404,
        )

    # Get filter parameters
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    entry_type = request.GET.get("type")
    page = int(request.GET.get("page", 1))
    per_page = 50

    # Build query
    query = Q(account=account)

    if start_date:
        query &= Q(created_at__date__gte=start_date)
    if end_date:
        query &= Q(created_at__date__lte=end_date)
    if entry_type:
        query &= Q(entry_type=entry_type)

    # Get entries with pagination
    entries = LedgerEntry.objects.filter(query).order_by("-created_at")

    # Calculate totals
    total_credits = entries.filter(entry_type=EntryType.CREDIT).aggregate(
        total=models.Sum("amount")
    )["total"] or 0
    total_debits = entries.filter(entry_type=EntryType.DEBIT).aggregate(
        total=models.Sum("amount")
    )["total"] or 0
    net_amount = total_credits - total_debits

    # Paginate
    total_entries = entries.count()
    entries = entries[(page - 1) * per_page : page * per_page]
    has_next = total_entries > page * per_page

    return render(
        request,
        "accounts/statement.html",
        {
            "account": account,
            "entries": entries,
            "total_entries": total_entries,
            "total_credits": total_credits,
            "total_debits": total_debits,
            "net_amount": net_amount,
            "page": page,
            "has_next": has_next,
            "start_date": start_date or "",
            "end_date": end_date or "",
        },
    )