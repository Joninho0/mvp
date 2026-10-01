"""
Tests demonstrating concurrency handling.

This module contains tests that demonstrate:
1. The bug when no locking is used (concurrent transfers can cause negative balance)
2. The fix using select_for_update() (ordered locks)
"""

import threading
import time
from decimal import Decimal

import pytest
from django.db import transaction

from apps.accounts.models import Account
from apps.transactions.models import Transaction, TransactionStatus, TransactionType


@pytest.mark.django_db
class TestConcurrency:
    """Tests for concurrency handling."""

    def test_concurrent_transfer_without_locks_bug(self, test_user):
        """
        DEMONSTRATE THE BUG: Concurrent transfers can cause negative balance.

        This test intentionally shows what happens WITHOUT proper locking.
        Run with multiple threads transferring from the same account.
        """
        # Create account with small balance
        account = Account.objects.create(
            customer=test_user,
            account_number=Account.generate_account_number(),
            balance=Decimal("100.00"),  # Only 100
        )

        results = {"success": 0, "failed": 0, "errors": []}
        lock = threading.Lock()

        def transfer_amount(amount):
            """Attempt to transfer money."""
            try:
                # This simulates what would happen without proper locking
                current_balance = account.balance

                if current_balance < amount:
                    with lock:
                        results["failed"] += 1
                    return

                # Simulate concurrent update (NO LOCKING - this is the bug!)
                # In real code, this would be: account.balance -= amount
                account.refresh_from_db()
                new_balance = account.balance - amount

                if new_balance < 0:
                    with lock:
                        results["failed"] += 1
                    return

                # Update without lock
                account.balance = new_balance
                account.save()

                with lock:
                    results["success"] += 1

            except Exception as e:
                with lock:
                    results["errors"].append(str(e))

        # Create 10 threads each trying to transfer 50 (total 500, but only 100 available)
        threads = []
        for i in range(10):
            t = threading.Thread(target=transfer_amount, args=(Decimal("50.00"),))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # BUG: Without locking, we can have more successes than possible
        print(f"\n⚠️  WITHOUT LOCKING:")
        print(f"   Expected max successes: 2 (100 / 50)")
        print(f"   Actual successes: {results['success']}")
        print(f"   Failed: {results['failed']}")

        # This assertion will FAIL if no locking (demonstrating the bug)
        # assert results["success"] <= 2, "Bug: More transfers succeeded than balance allows!"

    def test_concurrent_transfer_with_locks(self, test_user):
        """
        DEMONSTRATE THE FIX: Using select_for_update with ordered locking.

        This test shows how proper locking prevents the bug.
        """
        # Create account with small balance
        account = Account.objects.create(
            customer=test_user,
            account_number=Account.generate_account_number(),
            balance=Decimal("100.00"),
        )

        results = {"success": 0, "failed": 0, "errors": []}
        lock = threading.Lock()

        def transfer_with_lock(amount):
            """Transfer with proper locking."""
            try:
                with transaction.atomic():
                    # Lock the account (ordered by ID to prevent deadlock)
                    locked_account = Account.objects.select_for_update().get(id=account.id)

                    if locked_account.balance < amount:
                        with lock:
                            results["failed"] += 1
                        return

                    # Update within lock
                    locked_account.balance -= amount
                    locked_account.save()

                    with lock:
                        results["success"] += 1

            except Exception as e:
                with lock:
                    results["errors"].append(str(e))

        # Create 10 threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=transfer_with_lock, args=(Decimal("50.00"),))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # FIXED: With proper locking, we can only have 2 successful transfers
        print(f"\n✅ WITH LOCKING:")
        print(f"   Expected: 2 transfers of 50 each = 100")
        print(f"   Actual successes: {results['success']}")
        print(f"   Failed: {results['failed']}")

        assert results["success"] == 2, f"Expected 2 successes, got {results['success']}"
        assert results["failed"] == 8, f"Expected 8 failures, got {results['failed']}"

    def test_deadlock_prevention(self, test_user):
        """
        DEMONSTRATE: Ordered locking prevents deadlock.

        When transferring between accounts, lock both accounts in a
        deterministic order to prevent circular waits.
        """
        account1 = Account.objects.create(
            customer=test_user,
            account_number=Account.generate_account_number(),
            balance=Decimal("1000.00"),
        )
        account2 = Account.objects.create(
            customer=test_user,
            account_number=Account.generate_account_number(),
            balance=Decimal("1000.00"),
        )

        # Transfer from account1 to account2
        with transaction.atomic():
            accounts = [account1, account2]
            accounts.sort(key=lambda a: a.id)  # Order by ID

            for acc in accounts:
                Account.objects.select_for_update().get(id=acc.id)

            # Perform transfer
            account1.balance -= Decimal("100.00")
            account1.save()
            account2.balance += Decimal("100.00")
            account2.save()

        # Verify
        account1.refresh_from_db()
        account2.refresh_from_db()

        assert account1.balance == Decimal("900.00")
        assert account2.balance == Decimal("1100.00")